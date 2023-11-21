-- membres d'une structure : 
-- invité en tant que membre de structure, validé ou non
-- noqa: disable=LT05

drop table if exists mb_members_invited;

create table mb_members_invited as
select
    mu.id                                                 as "ID utilisateur",
    mu.email                                              as "E-mail",
    mu.is_valid                                           as "E-mail validé",
    mu.date_joined                                        as "Date de création",
    mu.last_login                                         as "Dernière connexion",
    ms.name                                               as "Nom de la structure",
    ms.dora_url                                           as "URL Dora",
    ms.department                                         as "Département",
    ss.creation_date                                      as "Date d'invitation",
    ss.is_admin                                           as "Invitation en tant qu'admin",
    ss.invited_by_admin                                   as "Invitation par un admin",
    (select mu.last_login < now() - interval '18 months') as "Compte inactif",
    (
        select count(*) > 0
        from structures_structuremember as ssm
        inner join mb_user as mu2 on ssm.user_id = mu2.id and mu2.is_valid
        where ssm.is_admin and ssm.structure_id = ms.id
    )                                                     as "Structure avec admin actif",
    (
        select count(*) from
            structures_structuremember as ss3
        where ss3.structure_id = ss.structure_id and ss3.is_admin
    )                                                     as "Nombre d'admins dans la structure",
    (
        select count(*) = 0 from
            structures_structuremember as ss3
        where ss3.structure_id = ss.structure_id and ss3.is_admin
    )                                                     as "Premier admin de la structure",
    (
        select count(*)
        from structures_structuremember as ss2
        where
            ss2.user_id = mu.id
    )                                                     as "Membre d'autres structures"
from mb_user as mu
inner join structures_structureputativemember as ss on mu.id = ss.user_id
left join mb_structure as ms on ss.structure_id = ms.id
where not mu.is_staff
order by mu.date_joined desc;

-- Indexes 

create index mb_members_invited_valide_idx on public.mb_members_invited (
    "E-mail validé"
);
create index mb_members_invited_date_joined_idx on public.mb_members_invited (
    "Date de création"
);
create index mb_members_invited_dpt_idx on public.mb_members_invited (
    "Département"
);
