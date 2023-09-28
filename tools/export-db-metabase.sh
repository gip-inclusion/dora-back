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
 SELECT
    services_service.id,
    services_service.name,
    services_service.short_desc,
    services_service.full_desc,
    services_service.is_cumulative,
    services_service.has_fee,
    services_service.fee_details,
    services_service.beneficiaries_access_modes_other,
    services_service.coach_orientation_modes_other,
    services_service.forms,
    services_service.contact_name,
    services_service.contact_phone,
    services_service.contact_email,
    services_service.is_contact_info_public,
    services_service.remote_url,
    services_service.address1,
    services_service.address2,
    services_service.postal_code,
    services_service.city_code,
    services_service.city,
    services_service.recurrence,
    services_service.suspension_date,
    services_service.creation_date,
    services_service.modification_date,
    services_service.creator_id,
    services_service.last_editor_id,
    services_service.structure_id,
    services_service.slug,
    services_service.online_form,
    services_service.publication_date,
    services_service.diffusion_zone_details,
    services_service.diffusion_zone_type,
    services_service.qpv_or_zrr,
    services_service.is_model,
    services_service.model_id,
    services_service.last_sync_checksum,
    services_service.sync_checksum,
    services_service.status,
    services_service.moderation_date,
    services_service.moderation_status,
    services_service.fee_condition_id,
    services_service.use_inclusion_numerique_scheme,
    services_service.source_id,
    services_service.data_inclusion_id,
    services_service.data_inclusion_source,
    -- TODO: deprecated
    (select services_service.status!='PUBLISHED') AS is_draft,
    (select services_service.status='SUGGESTION') AS is_suggestion,
    --
    (SELECT st_y((services_service.geom)::geometry) AS st_y) AS latitude,
    (SELECT st_x((services_service.geom)::geometry) AS st_x) AS longitude,
    (SELECT services_service.contact_name != '') AS has_contact_name,
    (SELECT services_service.contact_phone != '') AS has_contact_phone,
    (SELECT services_service.contact_email != '') AS has_contact_email,
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
 SELECT *,
   (SELECT concat('https://dora.inclusion.beta.gouv.fr/services/', slug)) as dora_url
   FROM mb_all_service where is_model is false"

psql $SRC_DB_URL -c "DROP VIEW IF EXISTS mb_model"
psql $SRC_DB_URL -c "
CREATE VIEW mb_model AS
SELECT
    id,
    name,
    short_desc,
    full_desc,
    is_cumulative,
    fee_details,
    beneficiaries_access_modes_other,
    coach_orientation_modes_other,
    forms,
    recurrence,
    suspension_date,
    creation_date,
    modification_date,
    creator_id,
    last_editor_id,
    structure_id,
    slug,
    online_form,
    qpv_or_zrr,
    sync_checksum,
    fee_condition_id,
   (SELECT concat('https://dora.inclusion.beta.gouv.fr/modeles/', slug)) as dora_url
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
  users_user.last_login,
  users_user.last_service_reminder_email_sent,
  (SELECT users_user.last_service_reminder_email_sent) AS last_notification_email_sent,
  users_user.newsletter,
  users_user.main_activity,
  -- TODO: deprecated
  (select FALSE) as is_bizdev
  --
 FROM users_user
 WHERE (users_user.is_active IS TRUE)"
psql $SRC_DB_URL -c "ALTER TABLE mb_user ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_user -c | psql $DEST_DB_URL

# aggregation des tables mobilisation d·i et dora
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_mobilisationevent_all"
psql $SRC_DB_URL -c "
CREATE TABLE mb_mobilisationevent_all AS
 SELECT
	( SELECT 'di-' :: text || stats_dimobilisationevent.id ) AS id,
	stats_dimobilisationevent.path,
	stats_dimobilisationevent.date,
	stats_dimobilisationevent.anonymous_user_hash,
	stats_dimobilisationevent.is_logged,
	stats_dimobilisationevent.is_staff,
	stats_dimobilisationevent.is_manager,
	stats_dimobilisationevent.is_an_admin,
	stats_dimobilisationevent.user_kind,
	stats_dimobilisationevent.structure_department,
	stats_dimobilisationevent.user_id,
	( SELECT true ) AS is_di
FROM
	stats_dimobilisationevent UNION
SELECT
	( SELECT 'dora-' :: text || stats_mobilisationevent.id ) AS id,
	stats_mobilisationevent.path,
	stats_mobilisationevent.date,
	stats_mobilisationevent.anonymous_user_hash,
	stats_mobilisationevent.is_logged,
	stats_mobilisationevent.is_staff,
	stats_mobilisationevent.is_manager,
	stats_mobilisationevent.is_an_admin,
	stats_mobilisationevent.user_kind,
	stats_mobilisationevent.structure_department,
	stats_mobilisationevent.user_id,
	( SELECT false ) AS is_di
FROM
	stats_mobilisationevent"
psql $SRC_DB_URL -c "ALTER TABLE mb_mobilisationevent_all ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_mobilisationevent_all -c | psql $DEST_DB_URL

psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_mobilisationevent_categories_all"
psql $SRC_DB_URL -c "
CREATE TABLE mb_mobilisationevent_categories_all AS
 SELECT
	( SELECT 'di-' :: text || stats_dimobilisationevent_categories.dimobilisationevent_id ) AS mobilisationevent_id,
	stats_dimobilisationevent_categories.servicecategory_id
FROM
	stats_dimobilisationevent_categories UNION
SELECT
	( SELECT 'dora-' :: text || stats_mobilisationevent_categories.mobilisationevent_id ) AS mobilisationevent_id,
	stats_mobilisationevent_categories.servicecategory_id
FROM
	stats_mobilisationevent_categories"
psql $SRC_DB_URL -c "ALTER TABLE mb_mobilisationevent_categories_all ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_mobilisationevent_categories_all -c | psql $DEST_DB_URL


pg_dump $DATABASE_URL -O -t orientations_orientation -t orientations_orientation_rejection_reasons -t orientations_rejectionreason -t orientations_sentcontactemail -t services_servicesource -t services_bookmark -t services_servicefee -t services_accesscondition -t services_beneficiaryaccessmode -t services_coachorientationmode -t services_concernedpublic -t services_credential -t services_locationkind -t services_requirement -t services_service_access_conditions -t services_service_beneficiaries_access_modes -t services_service_categories -t services_service_coach_orientation_modes -t services_service_concerned_public -t services_service_credentials -t services_service_kinds -t services_service_location_kinds -t services_service_requirements -t services_service_subcategories -t services_servicecategory -t services_servicekind -t services_servicemodificationhistoryitem -t services_servicestatushistoryitem -t services_servicesubcategory -t structures_structure_national_labels -t structures_structurenationallabel -t structures_structuremember -t structures_structureputativemember -t structures_structuresource -t structures_structuretypology -t stats_abtestgroup -t stats_deploymentstate -t stats_dimobilisationevent -t stats_dimobilisationevent_ab_test_groups -t stats_dimobilisationevent_categories -t stats_dimobilisationevent_subcategories -t stats_diserviceview -t stats_diserviceview_categories -t stats_diserviceview_subcategories -t stats_mobilisationevent -t stats_mobilisationevent_ab_test_groups -t stats_orientationview -t stats_pageview -t stats_searchview -t stats_searchview_categories -t stats_searchview_subcategories -t stats_serviceview -t stats_structureview  -c | psql $DEST_DB_URL
