#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Trace execution
[[ "${DEBUG}" ]] && set -x

# Only run on the production app
if [ "$ENVIRONMENT" != "production" ];then exit 0; fi

# Install the latest psql client
dbclient-fetcher psql

pg_dump "${DATABASE_URL}" \
    --clean \
    --no-owner \
    # use custom format to compress data
    --format=custom \
    -t orientations_orientation \
    -t orientations_orientation_rejection_reasons \
    -t orientations_rejectionreason \
    -t orientations_sentcontactemail \
    -t services_accesscondition \
    -t services_beneficiaryaccessmode \
    -t services_bookmark \
    -t services_coachorientationmode \
    -t services_concernedpublic \
    -t services_credential \
    -t services_locationkind \
    -t services_requirement \
    -t services_service \
    -t services_service_access_conditions \
    -t services_service_beneficiaries_access_modes \
    -t services_service_categories \
    -t services_service_coach_orientation_modes \
    -t services_service_concerned_public \
    -t services_service_credentials \
    -t services_service_kinds \
    -t services_service_location_kinds \
    -t services_service_requirements \
    -t services_service_subcategories \
    -t services_servicecategory \
    -t services_servicefee \
    -t services_servicekind \
    -t services_servicemodificationhistoryitem \
    -t services_servicesource \
    -t services_servicestatushistoryitem \
    -t services_servicesubcategory \
    -t stats_abtestgroup \
    -t stats_deploymentstate \
    -t stats_dimobilisationevent \
    -t stats_dimobilisationevent_ab_test_groups \
    -t stats_dimobilisationevent_categories \
    -t stats_dimobilisationevent_subcategories \
    -t stats_diserviceview \
    -t stats_diserviceview_categories \
    -t stats_diserviceview_subcategories \
    -t stats_mobilisationevent \
    -t stats_mobilisationevent_ab_test_groups \
    -t stats_orientationview \
    -t stats_pageview \
    -t stats_searchview \
    -t stats_searchview_categories \
    -t stats_searchview_subcategories \
    -t stats_serviceview \
    -t stats_structureview \
    -t structures_structure \
    -t structures_structure_national_labels \
    -t structures_structuremember \
    -t structures_structurenationallabel \
    -t structures_structureputativemember \
    -t structures_structuresource \
    -t structures_structuretypology \
    -t users_user \
    > ~/dump.sql

# TODO: encrypt with openssl ?

# TODO: add timestamp ?

curl https://dl.min.io/client/mc/release/linux-amd64/mc -o ~/mc
chmod +x ~/mc

~/mc alias set scaleway https://s3.fr-par.scw.cloud "${SCALEWAY_ACCESS_KEY}" "${SCALEWAY_SECRET_KEY}"

~/mc cp ~/dump.sql data-inclusion-lake/sources/dora/stats/dump.sql
