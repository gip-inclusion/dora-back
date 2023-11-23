-- Utilisateurs n'ayant pas validé leur email 
-- avant la mise en production d'inclusion-connect

-- noqa: disable=LT05

drop table if exists mb_users_before_ic;

create table mb_users_before_ic as
select
    mu.id          as "ID utilisateur",
    mu.email       as "E-mail",
    mu.date_joined as "Date de création",
    (
        case
            when mu.last_login is null then true
            else mu.last_login < now() - interval '18 months'
        end
    )              as "Compte inactif"
from mb_user as mu
where
    not mu.is_staff
    and mu.date_joined < '2022-10-03'
    and not mu.is_valid
order by mu.date_joined desc;

-- Indexes et PK

alter table public.mb_users_before_ic add constraint mb_users_before_ic_pk primary key ( -- noqa: LT05
    "ID utilisateur"
);
create index mb_users_before_ic_date_joined_idx on public.mb_users_before_ic (
    "Date de création"
);

comment on table mb_users_before_ic is 'Utilisateurs sans validation créé avant IC';
