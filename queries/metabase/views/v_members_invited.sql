-- membres d'une structure : 
-- invité en tant que membre de structure, validé ou non

drop view if exists v_members_invited;

create or replace view v_members_invited as
select
    mu.id               as "ID utilisateur",
    mu.email            as "E-mail",
    mu.date_joined      as "Date de création",
    mu.is_valid         as "Valide",
    ms.name             as "Nom de la structure",
    ms.dora_url         as "URL Dora",
    ms.department       as "Département",
    ss.creation_date    as "Date d'invitation",
    ss.is_admin         as "Invitation en tant qu'admin",
    ss.invited_by_admin as "Invitation par un admin",
    (
        select count(*) > 0
        from structures_structuremember as ssm
        inner join mb_user as mu2 on ssm.user_id = mu2.id and mu2.is_valid
        where ssm.is_admin and ssm.structure_id = ms.id
    )                   as "Structure avec admin actif"
from mb_user as mu
inner join structures_structureputativemember as ss on mu.id = ss.user_id
left join mb_structure as ms on ss.structure_id = ms.id
where not mu.is_staff
order by mu.date_joined desc;
