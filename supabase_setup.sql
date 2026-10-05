-- ClueSight only. Existing analytics_events is untouched.
-- Safe to run again when upgrading an existing installation.
begin;
create table if not exists public.cluesight_events (
    event_id uuid primary key, user_id uuid not null, event_type text not null,
    created_at timestamptz not null default now(), verification_pass boolean,
    verification_score integer check (verification_score between 0 and 100),
    attempts integer, mode text, first_image_seconds double precision,
    total_seconds double precision, app_version text
);

-- Upgrade the original image-generation-only schema for funnel events.
alter table public.cluesight_events drop constraint if exists cluesight_events_event_type_check;
alter table public.cluesight_events drop constraint if exists cluesight_events_attempts_check;
alter table public.cluesight_events drop constraint if exists cluesight_events_mode_check;
alter table public.cluesight_events drop constraint if exists cluesight_events_total_seconds_check;
alter table public.cluesight_events alter column attempts drop not null;
alter table public.cluesight_events alter column mode drop not null;
alter table public.cluesight_events add column if not exists app_version text;
alter table public.cluesight_events add constraint cluesight_events_event_type_check
    check (event_type in ('visit', 'analysis_completed', 'image_generated'));
alter table public.cluesight_events add constraint cluesight_events_attempts_check
    check (attempts is null or attempts between 1 and 3);
alter table public.cluesight_events add constraint cluesight_events_mode_check
    check (mode is null or mode in ('빠른 생성', '정밀 생성'));
alter table public.cluesight_events add constraint cluesight_events_total_seconds_check
    check (total_seconds is null or (total_seconds >= 0 and
        (first_image_seconds is null or total_seconds >= first_image_seconds)));

create index if not exists cluesight_events_user_date_idx on public.cluesight_events(user_id, created_at);
create index if not exists cluesight_events_funnel_idx on public.cluesight_events(event_type, app_version, user_id);
alter table public.cluesight_events enable row level security;
revoke all on public.cluesight_events from public, anon, authenticated;
grant select, insert on public.cluesight_events to service_role;

create or replace function public.cluesight_analytics_summary()
returns jsonb language sql stable security invoker set search_path = '' as $$
with all_events as (
    select *, (created_at at time zone 'Asia/Seoul')::date as usage_day
    from public.cluesight_events
), generations as (
    select * from all_events where event_type = 'image_generated'
), users as (
    select user_id, count(distinct usage_day) as days,
           count(distinct usage_day) filter (where created_at >= now() - interval '7 days') as weekly_days
    from generations group by user_id
), funnel as (
    select count(distinct user_id) filter (where event_type = 'visit') as visitors,
           count(distinct user_id) filter (where event_type = 'analysis_completed') as analysis_users
    from all_events where app_version = '2026.10.05'
), quality as (
    select count(*) filter (where created_at < timestamptz '2026-10-04 15:00:00+00') as before_generations,
           count(*) filter (where created_at >= timestamptz '2026-10-04 15:00:00+00') as after_generations,
           coalesce(avg(total_seconds) filter (where created_at < timestamptz '2026-10-04 15:00:00+00'), 0) as before_avg_seconds,
           coalesce(avg(total_seconds) filter (where created_at >= timestamptz '2026-10-04 15:00:00+00'), 0) as after_avg_seconds,
           coalesce(100.0 * count(*) filter (where created_at < timestamptz '2026-10-04 15:00:00+00' and verification_pass is true)
             / nullif(count(verification_pass) filter (where created_at < timestamptz '2026-10-04 15:00:00+00'), 0), 0) as before_pass_rate,
           coalesce(100.0 * count(*) filter (where created_at >= timestamptz '2026-10-04 15:00:00+00' and verification_pass is true)
             / nullif(count(verification_pass) filter (where created_at >= timestamptz '2026-10-04 15:00:00+00'), 0), 0) as after_pass_rate
    from generations
)
select jsonb_build_object(
    'visitors', (select visitors from funnel), 'analysis_users', (select analysis_users from funnel),
    'total_users', (select count(*) from users),
    'weekly_active_users', (select count(*) from users where weekly_days > 0),
    'returning_users', (select count(*) from users where days >= 2),
    'weekly_returning_users', (select count(*) from users where weekly_days >= 2),
    'total_generations', count(*),
    'verification_pass_rate', coalesce(100.0 * count(*) filter (where verification_pass is true)
        / nullif(count(verification_pass), 0), 0),
    'avg_attempts', coalesce(avg(attempts), 0),
    'before_generations', (select before_generations from quality),
    'after_generations', (select after_generations from quality),
    'before_avg_seconds', (select before_avg_seconds from quality),
    'after_avg_seconds', (select after_avg_seconds from quality),
    'before_pass_rate', (select before_pass_rate from quality),
    'after_pass_rate', (select after_pass_rate from quality)
) from generations;
$$;
revoke all on function public.cluesight_analytics_summary() from public, anon, authenticated;
grant execute on function public.cluesight_analytics_summary() to service_role;
commit;
