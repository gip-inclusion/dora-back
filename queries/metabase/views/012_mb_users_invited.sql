-- Détails du rattachement des membres à une structure : 
-- utilisateurs membres d'une structure, 
-- en attente de validation, 
-- ou sans aucun rattachement.

-- noqa: disable=LT05

drop table if exists mb_users_invited;

create table mb_users_invited as
select
    mu.id                               as "ID utilisateur",
    mu.email                            as "E-mail",
    mu.is_valid                         as "E-mail validé",
    mu.date_joined                      as "Date de création",
    mu.last_login                       as "Dernière connexion",
    (
        case
            when mu.last_login is null then true
            else mu.last_login < now() - interval '18 months'
        end
    )                                   as "Compte inactif",
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
create index mb_users_invited_valide_idx on public.mb_users_invited (
    "E-mail validé"
);
create index mb_users_invited_date_joined_idx on public.mb_users_invited (
    "Date de création"
);

comment on table mb_users_invited is 'Détails du rattachement des utilisateurs à une structure';
