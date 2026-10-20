-- ClueSight only. Existing analytics_events is untouched.
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
create or replace function public.cluesight_analytics_summary()
returns jsonb language sql stable security invoker set search_path = '' as $$
with events as (
    select *, (created_at at time zone 'Asia/Seoul')::date as usage_day
    from public.cluesight_events
    where event_type = 'image_generated'
      and not (
          verification_pass is false and verification_score = 0 and attempts = 1
          and mode = '빠른 생성' and first_image_seconds = 0 and total_seconds = 0
      )
), users as (
    select user_id, count(distinct usage_day) as days,
           count(distinct usage_day) filter (where created_at >= now() - interval '7 days') as weekly_days
    from events group by user_id
)
select jsonb_build_object(
    'total_users', (select count(*) from users),
    'weekly_active_users', (select count(*) from users where weekly_days > 0),
    'returning_users', (select count(*) from users where days >= 2),
    'weekly_returning_users', (select count(*) from users where weekly_days >= 2),
    'total_generations', count(*),
    'verification_pass_rate', coalesce(100.0 * count(*) filter (where verification_pass is true)
        / nullif(count(verification_pass), 0), 0),
    'avg_attempts', coalesce(avg(attempts), 0)
) from events;
$$;
revoke all on function public.cluesight_analytics_summary() from public, anon, authenticated;
grant execute on function public.cluesight_analytics_summary() to service_role;
-- Dedicated all-time site visit ledger. Visits never expire or reset by date.
create table if not exists public.cluesight_visits (
    event_id uuid primary key,
    user_id uuid not null,
    created_at timestamptz not null default now()
);
create index if not exists cluesight_visits_user_created_idx
    on public.cluesight_visits(user_id, created_at);
alter table public.cluesight_visits enable row level security;
revoke all on public.cluesight_visits from public, anon, authenticated;
grant select, insert on public.cluesight_visits to service_role;

-- Move legacy visit markers out of the generation count without deleting history.
insert into public.cluesight_visits(event_id, user_id, created_at)
select event_id, user_id, created_at
from public.cluesight_events
where event_type = 'image_generated'
  and verification_pass is false
  and verification_score = 0
  and attempts = 1
  and mode = '빠른 생성'
  and first_image_seconds = 0
  and total_seconds = 0
on conflict (event_id) do nothing;

create or replace function public.cluesight_visit_summary()
returns jsonb language sql stable security invoker set search_path = '' as $
with per_browser as (
    select user_id, count(*) as visit_count
    from public.cluesight_visits
    group by user_id
), totals as (
    select
        (select count(*) from per_browser) as total_users,
        (select count(*) from public.cluesight_visits) as total_visits,
        (select count(*) from per_browser where visit_count >= 2) as returning_users
)
select jsonb_build_object(
    'total_users', total_users,
    'total_visits', total_visits,
    'returning_users', returning_users,
    'retention', case when total_users > 0
        then 100.0 * returning_users / total_users else 0.0 end
)
from totals;
$$;
revoke all on function public.cluesight_visit_summary() from public, anon, authenticated;
grant execute on function public.cluesight_visit_summary() to service_role;

commit;
