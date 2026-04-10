alter table shifts
add column if not exists mode text;

update shifts
set mode = 'basic'
where mode is null;

alter table shifts
alter column mode set default 'basic';

alter table shifts
alter column mode set not null;

alter table shifts
drop constraint if exists shifts_mode_check;

alter table shifts
add constraint shifts_mode_check
check (mode in ('basic', 'advanced', 'advanced_research'));

alter table orders
add column if not exists position_district text null;

alter table orders
add column if not exists pickup_district text null;

alter table orders
add column if not exists dropoff_district text null;

alter table orders
drop constraint if exists orders_source_mode_check;

alter table orders
add constraint orders_source_mode_check
check (source_mode in ('basic', 'advanced', 'advanced_research'));

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
