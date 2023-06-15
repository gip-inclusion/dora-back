#!/bin/bash

# Only run on the production app
if [ "$ENVIRONMENT" != "production" ];then exit 0; fi

# Install the latest psql client
dbclient-fetcher psql

export SRC_DB_URL=$DATABASE_URL
export DEST_DB_URL=$METABASE_DB_URL

# mb_structure
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_structure"
psql $SRC_DB_URL -c "
CREATE TABLE mb_structure AS
SELECT structures_structure.*,
   (select concat('https://dora.inclusion.beta.gouv.fr/structures/', slug)) as dora_url
   FROM structures_structure"
psql $SRC_DB_URL -c "ALTER TABLE mb_structure ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_structure -c | psql $DEST_DB_URL

# mb_all_service
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_all_service CASCADE"
psql $SRC_DB_URL -c "
CREATE TABLE mb_all_service AS
 SELECT services_service.*,
    -- TODO: deprecated
    (select services_service.status!='PUBLISHED') AS is_draft,
    (select services_service.status='SUGGESTION') AS is_suggestion,
    --
    (SELECT st_y((services_service.geom)::geometry) AS st_y) AS latitude,
    (SELECT st_x((services_service.geom)::geometry) AS st_x) AS longitude,
    (SELECT services_service.contact_name != '') AS has_contact_name,
    (SELECT services_service.contact_phone != '') AS has_contact_phone,
    (SELECT services_service.contact_email != '') AS has_contact_email,
    (SELECT concat('https://dora.inclusion.beta.gouv.fr/services/', slug)) as dora_url,
    CASE
        WHEN services_service.modification_date + '240 days'  <= now() AND services_service.status = 'PUBLISHED' THEN 'REQUIRED'
        WHEN services_service.modification_date + '180 days'  <= now() AND services_service.status = 'PUBLISHED' THEN 'NEEDED'
        ELSE 'NOT_NEEDED'
    END as update_status
 FROM services_service"
psql $SRC_DB_URL -c "ALTER TABLE mb_all_service ADD PRIMARY KEY (id)"



# mb_model. Les modèles sont des services, mais les self joins sont mal gérés sur metabase…
# => on sépare les deux
psql $SRC_DB_URL -c "DROP VIEW IF EXISTS mb_service"
psql $SRC_DB_URL -c "
CREATE VIEW mb_service AS
 SELECT *
   FROM mb_all_service where is_model is false"

psql $SRC_DB_URL -c "DROP VIEW IF EXISTS mb_model"
psql $SRC_DB_URL -c "
CREATE VIEW mb_model AS
 SELECT *
   FROM mb_all_service where is_model is true"

pg_dump $DATABASE_URL -O -t mb_all_service -t mb_model -t mb_service -c | psql $DEST_DB_URL

# mb_service_suggestion
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_service_suggestion"
psql $SRC_DB_URL -c "
CREATE TABLE mb_service_suggestion AS
 SELECT service_suggestions_servicesuggestion.*
   FROM service_suggestions_servicesuggestion"
psql $SRC_DB_URL -c "ALTER TABLE mb_service_suggestion ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_service_suggestion -c | psql $DEST_DB_URL


# mb_user
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_user"
psql $SRC_DB_URL -c "
CREATE TABLE mb_user AS
 SELECT users_user.id,
  users_user.ic_id,
  users_user.email,
  users_user.last_name,
  users_user.first_name,
  users_user.is_valid,
  users_user.is_staff,
  users_user.is_manager,
  users_user.department,
  users_user.date_joined,
  users_user.last_notification_email_sent,
  users_user.newsletter,
  -- TODO: deprecated
  (select FALSE) as is_bizdev
  --
 FROM users_user
 WHERE (users_user.is_active IS TRUE)"
psql $SRC_DB_URL -c "ALTER TABLE mb_user ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_user -c | psql $DEST_DB_URL

pg_dump $DATABASE_URL -O -t service_servicesource -t services_bookmark -t services_servicefee -t services_accesscondition -t services_beneficiaryaccessmode -t services_coachorientationmode -t services_concernedpublic -t services_credential -t services_locationkind -t services_requirement -t services_service_access_conditions -t services_service_beneficiaries_access_modes -t services_service_categories -t services_service_coach_orientation_modes -t services_service_concerned_public -t services_service_credentials -t services_service_kinds -t services_service_location_kinds -t services_service_requirements -t services_service_subcategories -t services_servicecategory -t services_servicekind -t services_servicemodificationhistoryitem -t services_servicestatushistoryitem -t services_servicesubcategory -t structures_structure_national_labels -t structures_structurenationallabel -t structures_structuremember -t structures_structureputativemember -t structures_structuresource -t structures_structuretypology -t stats_deploymentstate -c | psql $DEST_DB_URL
