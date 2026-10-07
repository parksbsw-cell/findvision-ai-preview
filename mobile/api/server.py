"""Single-process mobile API. Private results expire after one hour."""
import os
import secrets
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, Field

from . import provider

SECRET = os.getenv('SESSION_SECRET') or secrets.token_hex(32)
signer = URLSafeTimedSerializer(SECRET, salt='findvision-mobile')
DB = os.getenv('MOBILE_DB_PATH', os.path.join(os.path.dirname(__file__), 'usage.sqlite3'))
lock = threading.RLock()
pool = ThreadPoolExecutor(max_workers=2)
slots = threading.BoundedSemaphore(2)
jobs = {}
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def database():
    con = sqlite3.connect(DB)
    con.execute('''CREATE TABLE IF NOT EXISTS visits (
        owner TEXT PRIMARY KEY, count INTEGER NOT NULL, last_visit REAL NOT NULL
    )''')
    return con


def count(owner):
    with database() as con:
        row = con.execute('SELECT count FROM visits WHERE owner=?', (owner,)).fetchone()
    return row[0] if row else 0


def record_visit(owner):
    now = time.time()
    with database() as con:
        con.execute('''INSERT INTO visits(owner, count, last_visit) VALUES (?, 1, ?)
            ON CONFLICT(owner) DO UPDATE SET
            count = count + CASE WHEN excluded.last_visit - visits.last_visit >= 1800 THEN 1 ELSE 0 END,
            last_visit = excluded.last_visit''', (owner, now))
        row = con.execute('SELECT count FROM visits WHERE owner=?', (owner,)).fetchone()
    return row[0]


def ready():
    return all(os.getenv(k) for k in (
        'CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_API_TOKEN'
    )) and len(os.getenv('MOBILE_ACCESS_KEY', '')) >= 20


@app.middleware('http')
async def protect(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        expected_key = os.getenv('MOBILE_ACCESS_KEY', '')
        supplied_key = request.headers.get('authorization', '').removeprefix('Bearer ').strip()
        if not expected_key or not secrets.compare_digest(supplied_key, expected_key):
            return JSONResponse({'detail': '앱 연결 코드가 올바르지 않습니다.'}, status_code=401)
        origin = request.headers.get('origin')
        forwarded_proto = request.headers.get('x-forwarded-proto', request.url.scheme).split(',')[0].strip()
        host = request.headers.get('host', request.url.netloc)
        expected = os.getenv('PUBLIC_ORIGIN', f'{forwarded_proto}://{host}'.rstrip('/'))
        if request.method == 'POST' and (origin != expected or request.headers.get('x-findvision') != '1'):
            return JSONResponse({'detail': '앱 화면에서 다시 요청해 주세요.'}, status_code=403)
        try:
            request.state.owner = signer.loads(request.cookies.get('fv_session', ''), max_age=31536000)
        except BadSignature:
            request.state.owner = secrets.token_hex(24)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.set_cookie('fv_session', signer.dumps(request.state.owner), httponly=True,
                            secure=expected.startswith('https://'), samesite='strict', max_age=31536000)
    else:
        response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response


def admit(request, kind):
    if not ready():
        raise HTTPException(503, 'AI 연결 준비 중입니다. 현재는 화면을 둘러볼 수 있습니다.')
    with lock:
        now = time.time()
        for key in list(jobs):
            if jobs[key]['state'] in ('done', 'error') and now - jobs[key]['created'] > 3600:
                del jobs[key]
        if not slots.acquire(blocking=False):
            raise HTTPException(429, '다른 요청을 처리 중입니다. 잠시 후 다시 시도해 주세요.')


class Analysis(BaseModel):
    text: str = Field(min_length=1, max_length=1500)


class Generation(BaseModel):
    features: dict[str, str]
    mode: Literal['fast', 'precise'] = 'fast'


@app.get('/api/session')
def session(request: Request):
    visits = record_visit(request.state.owner)
    return {'ready': ready(), 'count': visits, 'labels': {
        k: provider.LABELS[k] for k in provider.EDITABLE_FIELDS}}


@app.post('/api/analyze')
def analyze(body: Analysis, request: Request):
    if not body.text.strip():
        raise HTTPException(422, '원문을 입력해 주세요.')
    admit(request, 'analyze')
    try:
        features = provider.extract_features(body.text.strip())
        return {'features': {k: features.get(k, '') for k in provider.EDITABLE_FIELDS}}
    except Exception:
        raise HTTPException(502, '분석을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.') from None
    finally:
        slots.release()


def generate(job_id, features, mode):
    started = time.perf_counter()
    best = None
    correction = ''
    first = None
    width, height = (512, 768) if mode == 'fast' else (768, 1024)
    try:
        for attempt in range(1, 2 if mode == 'fast' else 4):
            with lock:
                jobs[job_id]['progress'] = f'{attempt}차 이미지 생성 중'
            try:
                raw, b64, mime = provider.generate_image(provider.build_generation_prompt(features, '', correction), width, height)
            except Exception:
                if best is not None:
                    with lock:
                        jobs[job_id]['interrupted'] = True
                    break
                raise
            if first is None:
                first = time.perf_counter() - started
            verdict = {'available': False, 'pass': False, 'score': 0, 'missing': [], 'wrong': [], 'skipped': mode == 'fast'}
            if mode == 'precise':
                with lock:
                    jobs[job_id]['progress'] = f'{attempt}차 이미지 검수 중'
                try:
                    verdict = provider.verify_image(b64, mime, features)
                except Exception:
                    pass
            candidate = {'image': raw, 'mime': mime, 'verdict': verdict}
            if best is None or (verdict['pass'], verdict['available'], verdict['score']) > (best['verdict']['pass'], best['verdict']['available'], best['verdict']['score']):
                best = candidate
            with lock:
                jobs[job_id]['attempts'] = attempt
            if mode == 'fast' or verdict['pass'] or not verdict['available']:
                break
            correction = verdict.get('feedback_en', '')
        with lock:
            job = jobs[job_id]
            job.update(best, state='done', first_seconds=round(first, 1), total_seconds=round(time.perf_counter() - started, 1))
    except Exception as exc:
        with lock:
            jobs[job_id].update(state='error', error='이미지 제공자의 안전 검사로 생성이 중단되었습니다.' if '안전 검사' in str(exc) else '이미지를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    finally:
        slots.release()


@app.post('/api/generate', status_code=202)
def start(body: Generation, request: Request):
    if len(body.features) > len(provider.EDITABLE_FIELDS) or any(k not in provider.EDITABLE_FIELDS or len(v) > 300 for k, v in body.features.items()):
        raise HTTPException(422, '특징 입력을 확인해 주세요. 항목당 300자까지 가능합니다.')
    features = provider.sync_prompt_text_from_structured_features(body.features.copy())
    admit(request, 'generate')
    key = secrets.token_urlsafe(24)
    with lock:
        jobs[key] = {'owner': request.state.owner, 'state': 'running', 'progress': '생성 준비 중', 'created': time.time(), 'mode': body.mode}
    pool.submit(generate, key, features, body.mode)
    return {'id': key}


def own_job(key, owner):
    job = jobs.get(key)
    if not job or job['owner'] != owner or time.time() - job['created'] > 3600:
        raise HTTPException(404, '결과 보관 시간이 지났거나 접근할 수 없습니다.')
    return job


@app.get('/api/jobs/{key}')
def status(key: str, request: Request):
    with lock:
        job = own_job(key, request.state.owner)
        return {k: v for k, v in job.items() if k not in ('owner', 'image', 'mime')}


@app.get('/api/jobs/{key}/image')
def result_image(key: str, request: Request):
    with lock:
        job = own_job(key, request.state.owner)
        if job['state'] != 'done':
            raise HTTPException(409, '아직 생성 중입니다.')
        return Response(job['image'], media_type=job['mime'])


@app.get('/healthz')
def health():
    return {'status': 'ok'}


@app.get('/')
def root():
    return {'service': 'FindVision AI mobile bridge', 'status': 'ok' if ready() else 'setup_required'}
