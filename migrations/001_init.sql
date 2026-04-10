create table if not exists users (
    id bigint generated always as identity primary key,
    telegram_id bigint not null unique,
    username text null,
    first_name text null,
    role text not null default 'basic' check (role in ('basic', 'advanced')),
    plan text not null default 'free',
    created_at timestamptz not null default now()
);

create table if not exists shifts (
    id bigint generated always as identity primary key,
    user_id bigint not null references users(id),
    mode text not null default 'basic' check (mode in ('basic', 'advanced', 'advanced_research')),
    start_time timestamptz not null,
    end_time timestamptz null,
    duration_minutes integer null,
    orders_count integer not null default 0,
    earnings_total numeric(12, 2) null,
    city text null,
    weather_summary text null,
    weather_temp numeric(6, 2) null,
    weather_rain boolean null,
    status text not null default 'active' check (status in ('active', 'closed', 'auto_closed')),
    created_at timestamptz not null default now()
);

create unique index if not exists ux_shifts_one_active_per_user
on shifts(user_id)
where status = 'active';

create index if not exists ix_shifts_user_id on shifts(user_id);
create index if not exists ix_shifts_start_time on shifts(start_time);

create table if not exists orders (
    id bigint generated always as identity primary key,
    user_id bigint not null references users(id),
    shift_id bigint not null references shifts(id),
    ts timestamptz not null,
    district text null,
    position_district text null,
    pickup_district text null,
    dropoff_district text null,
    platform text null check (platform in ('Wolt', 'Glovo')),
    order_earnings numeric(12, 2) null,
    source_mode text not null check (source_mode in ('basic', 'advanced', 'advanced_research')),
    created_at timestamptz not null default now()
);

create index if not exists ix_orders_user_id on orders(user_id);
create index if not exists ix_orders_shift_id on orders(shift_id);
create index if not exists ix_orders_ts on orders(ts);

create or replace function average_earnings_per_hour_before_shift(
    p_user_id bigint,
    p_shift_id bigint
)
returns numeric
language sql
stable
as $$
    select avg(earnings_total / nullif(duration_minutes::numeric / 60, 0))
    from shifts
    where user_id = p_user_id
      and id <> p_shift_id
      and status in ('closed', 'auto_closed')
      and earnings_total is not null
      and duration_minutes > 0;
$$;

create or replace function get_personal_stats(
    p_user_id bigint
)
returns table (
    shifts_count bigint,
    orders_count bigint,
    total_earnings numeric,
    avg_eph numeric
)
language sql
stable
as $$
    select
        count(id) as shifts_count,
        coalesce(sum(orders_count), 0) as orders_count,
        coalesce(sum(earnings_total), 0) as total_earnings,
        coalesce(avg(earnings_total / nullif(duration_minutes::numeric / 60, 0)), 0) as avg_eph
    from shifts
    where user_id = p_user_id
      and status in ('closed', 'auto_closed');
$$;

create or replace function close_active_shift(
    p_telegram_id bigint,
    p_earnings_total numeric
)
returns setof shifts
language plpgsql
as $$
declare
    v_user_id bigint;
    v_shift_id bigint;
    v_now timestamptz := now();
    v_minutes integer;
begin
    select id into v_user_id
    from users
    where telegram_id = p_telegram_id;

    if v_user_id is null then
        return;
    end if;

    select id into v_shift_id
    from shifts
    where user_id = v_user_id
      and status = 'active'
    order by start_time desc
    limit 1
    for update;

    if v_shift_id is null then
        return;
    end if;

    select greatest(1, floor(extract(epoch from (v_now - start_time)) / 60)::integer)
    into v_minutes
    from shifts
    where id = v_shift_id;

    return query
    update shifts
    set end_time = v_now,
        duration_minutes = v_minutes,
        earnings_total = p_earnings_total,
        status = 'closed'
    where id = v_shift_id
    returning *;
end;
$$;

create or replace function create_order_for_telegram_user(
    p_telegram_id bigint,
    p_source_mode text,
    p_district text default null,
    p_position_district text default null,
    p_pickup_district text default null,
    p_dropoff_district text default null,
    p_platform text default null,
    p_order_earnings numeric default null
)
returns setof orders
language plpgsql
as $$
declare
    v_user_id bigint;
    v_shift_id bigint;
    v_order orders%rowtype;
begin
    select id into v_user_id
    from users
    where telegram_id = p_telegram_id;

    if v_user_id is null then
        raise exception 'User not found';
    end if;

    select id into v_shift_id
    from shifts
    where user_id = v_user_id
      and status = 'active'
    order by start_time desc
    limit 1
    for update;

    if v_shift_id is null then
        raise exception 'Active shift not found';
    end if;

    insert into orders (
        user_id,
        shift_id,
        ts,
        district,
        position_district,
        pickup_district,
        dropoff_district,
        platform,
        order_earnings,
        source_mode
    )
    values (
        v_user_id,
        v_shift_id,
        now(),
        coalesce(p_district, p_position_district),
        p_position_district,
        p_pickup_district,
        p_dropoff_district,
        p_platform,
        p_order_earnings,
        p_source_mode
    )
    returning * into v_order;

    update shifts
    set orders_count = orders_count + 1
    where id = v_shift_id;

    return next v_order;
end;
$$;
