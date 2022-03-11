#!/bin/bash

# Only run on the production app
if [ "$ENVIRONMENT" != "production" ];then exit 0; fi

export SRC_DB_URL=$DATABASE_URL
export DEST_DB_URL=$METABASE_DB_URL

# mb_structure
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_structure"
psql $SRC_DB_URL -c "
CREATE TABLE mb_structure AS
SELECT structures_structure.id,
    structures_structure.siret,
    structures_structure.name,
    structures_structure.short_desc,
    structures_structure.url,
    structures_structure.full_desc,
    structures_structure.postal_code,
    structures_structure.city_code,
    structures_structure.city,
    structures_structure.creation_date,
    structures_structure.modification_date,
    structures_structure.creator_id,
    structures_structure.address1,
    structures_structure.address2,
    structures_structure.last_editor_id,
    structures_structure.ape,
    structures_structure.latitude,
    structures_structure.longitude,
    structures_structure.slug,
    structures_structure.code_safir_pe,
    structures_structure.department,
    structures_structure.is_antenna,
    structures_structure.parent_id,
    structures_structure.source_id,
    structures_structure.typology_id
   FROM structures_structure"
psql $SRC_DB_URL -c "ALTER TABLE mb_structure ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_structure -c | psql $DEST_DB_URL


# mb_service
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_service"
psql $SRC_DB_URL -c "
CREATE TABLE mb_service AS
 SELECT services_service.id,
    services_service.name,
    services_service.short_desc,
    services_service.full_desc,
    services_service.is_cumulative,
    services_service.has_fee,
    services_service.fee_details,
    services_service.beneficiaries_access_modes_other,
    services_service.coach_orientation_modes_other,
    services_service.forms,
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
    services_service.is_draft,
    services_service.publication_date,
    services_service.is_suggestion,
    services_service.diffusion_zone_details,
    services_service.diffusion_zone_type,
    services_service.qpv_or_zrr,
    ( SELECT st_y((services_service.geom)::geometry) AS st_y) AS latitude,
    ( SELECT st_x((services_service.geom)::geometry) AS st_x) AS longitude
   FROM services_service"
psql $SRC_DB_URL -c "ALTER TABLE mb_service ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_service -c | psql $DEST_DB_URL

# mb_service
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_service_suggestion"
psql $SRC_DB_URL -c "
CREATE TABLE mb_service_suggestion AS
 SELECT service_suggestions_servicesuggestion.id,
    service_suggestions_servicesuggestion.siret,
    service_suggestions_servicesuggestion.name,
    service_suggestions_servicesuggestion.creation_date,
    service_suggestions_servicesuggestion.creator_id
   FROM service_suggestions_servicesuggestion"
psql $SRC_DB_URL -c "ALTER TABLE mb_service_suggestion ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_service_suggestion -c | psql $DEST_DB_URL


# mb_user
psql $SRC_DB_URL -c "DROP TABLE IF EXISTS mb_user"
psql $SRC_DB_URL -c "
CREATE TABLE mb_user AS
 SELECT users_user.id,
    users_user.is_valid,
    users_user.is_staff,
    users_user.is_bizdev,
    users_user.last_login,
    users_user.date_joined,
    users_user.newsletter
   FROM users_user
  WHERE (users_user.is_active IS TRUE)"
psql $SRC_DB_URL -c "ALTER TABLE mb_user ADD PRIMARY KEY (id)"

pg_dump $DATABASE_URL -O -t mb_user -c | psql $DEST_DB_URL

pg_dump $DATABASE_URL -O -t services_accesscondition -t services_beneficiaryaccessmode -t services_coachorientationmode -t services_concernedpublic -t services_credential -t services_locationkind -t services_requirement -t services_service_access_conditions -t services_service_beneficiaries_access_modes -t services_service_categories -t services_service_coach_orientation_modes -t services_service_concerned_public -t services_service_credentials -t services_service_kinds -t services_service_location_kinds -t services_service_requirements -t services_service_subcategories -t services_servicecategory -t services_servicekind -t services_servicemodificationhistoryitem -t services_servicesubcategory -t structures_structuremember -t structures_structureputativemember -t structures_structuresource -t structures_structuretypology -c | psql $DEST_DB_URL
