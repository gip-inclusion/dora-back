select distinct on ( email ) email, "users_user"."first_name", "users_user"."last_name", "users_user".newsletter
from "services_service"
         join "users_user" on "services_service"."creator_id" = "users_user"."id" or
                              "services_service"."last_editor_id" = "users_user"."id"
where "services_service".status = 'PUBLISHED'
  and "users_user".email != 'dora-bot@dora.beta.gouv.fr'

union

select distinct on ( "users_user".email ) email,
                                          "users_user"."first_name",
                                          "users_user"."last_name",
                                          "users_user".newsletter
from "services_service"
         join "structures_structuremember"
              on "services_service"."structure_id" = "structures_structuremember"."structure_id"
         join "users_user" on "structures_structuremember"."user_id" = "users_user"."id"
where "services_service".status = 'PUBLISHED'
  and "users_user".email != 'dora-bot@dora.beta.gouv.fr'
  and "structures_structuremember"."is_admin" is true
