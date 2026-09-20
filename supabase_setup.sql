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
    from public.cluesight_events where event_type = 'image_generated'
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
commit;
