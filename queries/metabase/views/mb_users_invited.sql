-- utilisateurs : 
-- membres d'une structure ou en attente, avec infos complémentaires

drop table if exists mb_users_invited;

create table mb_users_invited as
select
    mu.id                               as "ID utilisateur",
    mu.email                            as "E-mail",
    mu.is_valid                         as "E-mail validé",
    mu.date_joined                      as "Date de création",
    mu.last_login                       as "Dernière connexion",
    (select ic_id is not null)          as "Inscrit IC",
    (select date_joined < '2022-10-03') as "Créé avant MEP IC",
    (
        select id in (select user_id from structures_structuremember)
    )                                   as "Membre d'une structure",
    (
        select id in (select user_id from structures_structureputativemember)
    )                                   as "En attente de rattachement"
from mb_user as mu
where not mu.is_staff
order by mu.date_joined desc;

-- Indexes et PK

alter table public.mb_users_invited add constraint mb_users_invited_pk primary key ( -- noqa: LT05
    "ID utilisateur"
);
create index mb_users_invited_valide_idx on public.mb_users_invited ("Valide");
create index mb_users_invited_date_joined_idx on public.mb_users_invited (
    "Date de création"
);
