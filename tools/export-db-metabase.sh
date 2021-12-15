#!/bin/bash

# Only run on the production app
if [ "$ENVIRONMENT" != "production" ];then exit 0; fi

export SRC_DB_URL=$DATABASE_URL
export DEST_DB_URL=$METABASE_DB_URL


# analytics_structure
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS analytics_structure"
psql $SRC_DB_URL -c "
CREATE TABLE analytics_structure AS
SELECT
  structures_structure.id,
  structures_structure.siret,
  structures_structure.name,
  structures_structure.slug,
  structures_structure.short_desc,
  structures_structure.city_code,
  structures_structure.city,
  structures_structure.creation_date,
  structures_structure.modification_date,
  structures_structure.ape,
  structures_structure.latitude,
  structures_structure.longitude,
  structures_structure.typology,
  structures_structure.source,
  structures_structure.department,
  creator.is_staff AS staff_created,
  last_editor.is_staff AS staff_edited
FROM ((structures_structure
  LEFT JOIN users_user creator ON ((creator.id = structures_structure.creator_id)))
  LEFT JOIN users_user last_editor ON ((last_editor.id = structures_structure.last_editor_id)))"
psql $SRC_DB_URL -c "ALTER TABLE analytics_structure ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t analytics_structure -c | psql $DEST_DB_URL


# analytics_member
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS analytics_member"
psql $SRC_DB_URL -c "
CREATE TABLE analytics_member AS
SELECT
  structures_structuremember.id,
  structures_structuremember.is_admin,
  structures_structuremember.structure_id,
  structures_structuremember.user_id,
  structures_structuremember.has_accepted_invitation AS is_valid,
  structures_structuremember.creation_date,
  users_user.is_staff,
  structures_structure.department,
  structures_structure.typology
FROM ((structures_structuremember
  JOIN structures_structure ON ((structures_structure.id = structures_structuremember.structure_id)))
  JOIN users_user ON ((users_user.id = structures_structuremember.user_id)))"
psql $SRC_DB_URL -c "ALTER TABLE analytics_member ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t analytics_member -c | psql $DEST_DB_URL


# analytics_orphan_structure
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS analytics_orphan_structure"
psql $SRC_DB_URL -c "
CREATE TABLE analytics_orphan_structure AS
SELECT
  structures_structure.siret
FROM ((structures_structure
  LEFT JOIN structures_structuremember ON ((structures_structure.id = structures_structuremember.structure_id)))
  LEFT JOIN users_user ON ((structures_structuremember.user_id = users_user.id)))
GROUP BY structures_structure.siret
HAVING (count(*) FILTER (WHERE ((structures_structuremember.is_admin IS TRUE) AND (users_user.is_staff IS FALSE) AND (structures_structuremember.has_accepted_invitation = true) AND (users_user.is_valid = true) AND (users_user.is_active = true))) = 0)
ORDER BY structures_structure.siret"
psql $SRC_DB_URL -c "ALTER TABLE analytics_orphan_structure ADD PRIMARY KEY (siret)"

pg_dump $DATABASE_URL -O -t analytics_orphan_structure -c | psql $DEST_DB_URL


# analytics_service
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS analytics_service"
psql $SRC_DB_URL -c "
CREATE TABLE analytics_service AS
SELECT
  services_service.id,
  services_service.name,
  services_service.short_desc,
  services_service.category,
  services_service.kinds,
  services_service.subcategories,
  services_service.city_code,
  services_service.city,
  services_service.creation_date,
  services_service.modification_date,
  services_service.publication_date,
  services_service.structure_id,
  structures_structure.department,
  (SELECT st_y((services_service.geom)::geometry) AS st_y) AS latitude,
  (SELECT st_x((services_service.geom)::geometry) AS st_x) AS longitude,
  (SELECT (NOT services_service.is_draft)) AS published,
  creator.is_staff AS staff_created,
  last_editor.is_staff AS staff_edited,
  (SELECT ((services_service.modification_date - services_service.creation_date) > '1 day'::interval)) AS modified
FROM (((services_service
  LEFT JOIN users_user creator ON ((creator.id = services_service.creator_id)))
  LEFT JOIN users_user last_editor ON ((last_editor.id = services_service.last_editor_id)))
  LEFT JOIN structures_structure ON ((services_service.structure_id = structures_structure.id)))"
psql $SRC_DB_URL -c "ALTER TABLE analytics_service ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t analytics_service -c | psql $DEST_DB_URL


# analytics_user
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS analytics_user"
psql $SRC_DB_URL -c "
CREATE TABLE analytics_user AS
SELECT
  users_user.id,
  users_user.is_staff,
  users_user.is_active,
  users_user.date_joined,
  users_user.is_valid
FROM users_user"
psql $SRC_DB_URL -c "ALTER TABLE analytics_user ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t analytics_user -c | psql $DEST_DB_URL
