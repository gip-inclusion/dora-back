-- Exporte les coordonnées de tous les utilisateurs actifs dont l'email a été validé, ainsi
-- que les informations sur une de leurs structures


select distinct on (u.email)
       u.first_name as prénom,
       u.last_name as nom,
       u.email as courriel,
       u.phone_number as téléphone,
       s.name as structure,
       s.siret as SIRET,
       s.department as département,
       t.label as typologie,
       m.is_admin as administrateur
from structures_structuremember m
         inner join structures_structure s on m.structure_id = s.id  and department != ''
         inner join users_user u on m.user_id = u.id
         left join structures_structuretypology t on s.typology_id = t.id
where u.is_active
  and u.is_valid
order by u.email
