-- Extrait les courriels des createurs ou derniers editeurs des services publiés et non modifiés depuis plus de 6 mois,
-- ainsi que des administrateurs des structures concernées.

-- emails extraits du champ "creator_id" ou "last_editor_id" des services
select distinct on ( email ) email, u."first_name", u."last_name", u.newsletter
from "services_service" s
         join "users_user" u on s."last_editor_id" = u."id"
where s.status = 'PUBLISHED'
  and s.modification_date < now() - interval '6 months'
  and u.email != 'dora-bot@dora.beta.gouv.fr'
-----
union
-----
-- emails des administrateurs des structures concernées
select distinct on ( u.email ) email, u."first_name", u."last_name", u.newsletter
from "services_service" s
         join "structures_structuremember" sm on s."structure_id" = sm."structure_id"
         join "users_user" u on sm."user_id" = u."id"
where s.status = 'PUBLISHED'
  and s.modification_date < now() - interval '6 months'
  and u.email != 'dora-bot@dora.beta.gouv.fr'
  and sm."is_admin" is true;
