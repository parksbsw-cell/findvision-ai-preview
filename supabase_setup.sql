-- FindVision AI anonymous usage analytics. Existing tables are left untouched.
begin;

create table if not exists public.cluesight_events (
    event_id uuid primary key,
    user_id uuid not null,
    event_type text not null check (event_type = 'image_generated'),
    created_at timestamptz not null default now(),
    verification_pass boolean,
    verification_score integer check (verification_score between 0 and 100),
    attempts integer not null check (attempts between 1 and 3),
    mode text not null check (mode in ('빠른 생성', '정밀 생성')),
    first_image_seconds double precision check (first_image_seconds >= 0),
    total_seconds double precision check (total_seconds >= first_image_seconds)
);
create index if not exists cluesight_events_user_date_idx on public.cluesight_events(user_id, created_at);
alter table public.cluesight_events enable row level security;
revoke all on public.cluesight_events from public, anon, authenticated;
grant select, insert on public.cluesight_events to service_role;

create table if not exists public.findvision_visits (
    event_id uuid primary key,
    user_id uuid not null,
    created_at timestamptz not null default now()
);
create index if not exists findvision_visits_user_date_idx
    on public.findvision_visits(user_id, created_at);
alter table public.findvision_visits enable row level security;
revoke all on public.findvision_visits from public, anon, authenticated;
grant select, insert on public.findvision_visits to service_role;

create or replace function public.cluesight_record_visit(p_user_id uuid, p_event_id uuid)
returns bigint
language plpgsql volatile security invoker set search_path = '' as $$
declare visit_total bigint;
begin
    insert into public.findvision_visits(event_id, user_id)
    values (p_event_id, p_user_id)
    on conflict (event_id) do nothing;
    select count(*) into visit_total from public.findvision_visits where user_id = p_user_id;
    return visit_total;
end;
$$;
revoke all on function public.cluesight_record_visit(uuid, uuid) from public, anon, authenticated;
grant execute on function public.cluesight_record_visit(uuid, uuid) to service_role;

create or replace function public.cluesight_analytics_summary()
returns jsonb language sql stable security invoker set search_path = '' as $$
with visits as (
    select user_id, created_at, (created_at at time zone 'Asia/Seoul')::date as visit_day
    from public.findvision_visits
), users as (
    select user_id,
           count(distinct visit_day) as visit_days,
           count(*) filter (where created_at >= now() - interval '7 days') as weekly_visits,
           count(distinct visit_day) filter (
               where created_at >= now() - interval '7 days'
           ) as weekly_visit_days
    from visits group by user_id
)
select jsonb_build_object(
    'total_users', (select count(*) from users),
    'weekly_active_users', (select count(*) from users where weekly_visits > 0),
    'returning_users', (select count(*) from users where visit_days >= 2),
    'weekly_returning_users', (select count(*) from users where weekly_visit_days >= 2),
    'total_visits', (select count(*) from visits),
    'total_generations', (select count(*) from public.cluesight_events where event_type = 'image_generated'),
    'verification_pass_rate', coalesce(
        100.0 * (select count(*) from public.cluesight_events
                 where event_type = 'image_generated' and verification_pass is true)
        / nullif((select count(*) from public.cluesight_events
                  where event_type = 'image_generated' and verification_pass is not null), 0), 0
    ),
    'avg_attempts', coalesce((select avg(attempts) from public.cluesight_events
                              where event_type = 'image_generated'), 0)
);
$$;
revoke all on function public.cluesight_analytics_summary() from public, anon, authenticated;
grant execute on function public.cluesight_analytics_summary() to service_role;

commit;
