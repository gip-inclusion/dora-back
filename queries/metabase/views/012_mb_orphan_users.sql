-- Utilisateurs sans rattachements ni invitations
-- e-mail validé ou non

-- noqa: disable=LT05

drop table if exists mb_orphan_users;

create table mb_orphan_users as
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
    (select date_joined < '2022-10-03') as "Créé avant MEP IC"
from mb_user as mu
where
    not mu.is_staff
    and mu.id not in (select user_id from structures_structuremember)
    and mu.id not in (select user_id from structures_structureputativemember)
order by mu.date_joined desc;

-- Indexes et PK

alter table public.mb_orphan_users add constraint mb_orphan_users_pk primary key ( -- noqa: LT05
    "ID utilisateur"
);
create index mb_orphan_users_valide_idx on public.mb_orphan_users (
    "E-mail validé"
);
create index mb_orphan_users_date_joined_idx on public.mb_orphan_users (
    "Date de création"
);

comment on table mb_orphan_users is 'Détails du rattachement des utilisateurs à une structure';
