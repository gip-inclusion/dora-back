-- utilisateurs : 
-- membres d'une structure ou en attente, avec infos complémentaires

drop view if exists v_users_invited;

create view v_users_invited as
select
    mu.id                               as "ID utilisateur",
    mu.email                            as "E-mail",
    mu.date_joined                      as "Date de création",
    mu.is_valid                         as "Valide",
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
