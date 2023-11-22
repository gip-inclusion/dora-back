#!/bin/bash

# Seulement pour l'app de production 
if [ "$ENVIRONMENT" != "production" ];then exit 0; fi

# A NE PAS UTILISER DIRECTEMENT (sans bonne raison) : 
# script lancé par 'update-metabase-db.sh`

export DEST_DB_URL=$METABASE_DB_URL

# Export des tables de production vers METABASE
pg_dump $DATABASE_URL -O -t orientations_orientation -t orientations_orientation_rejection_reasons -t orientations_rejectionreason -t orientations_sentcontactemail -t services_servicesource -t services_bookmark -t services_servicefee -t services_accesscondition -t services_beneficiaryaccessmode -t services_coachorientationmode -t services_concernedpublic -t services_credential -t services_locationkind -t services_requirement -t services_service_access_conditions -t services_service_beneficiaries_access_modes -t services_service_categories -t services_service_coach_orientation_modes -t services_service_concerned_public -t services_service_credentials -t services_service_kinds -t services_service_location_kinds -t services_service_requirements -t services_service_subcategories -t services_servicecategory -t services_servicekind -t services_servicemodificationhistoryitem -t services_servicestatushistoryitem -t services_servicesubcategory -t structures_structure_national_labels -t structures_structurenationallabel -t structures_structuremember -t structures_structureputativemember -t structures_structuresource -t structures_structuretypology -t stats_abtestgroup -t stats_deploymentstate -t stats_dimobilisationevent -t stats_dimobilisationevent_ab_test_groups -t stats_dimobilisationevent_categories -t stats_dimobilisationevent_subcategories -t stats_diserviceview -t stats_diserviceview_categories -t stats_diserviceview_subcategories -t stats_mobilisationevent -t stats_mobilisationevent_ab_test_groups -t stats_mobilisationevent_categories -t stats_mobilisationevent_subcategories -t stats_orientationview -t stats_orientationview_categories -t stats_orientationview_subcategories -t stats_pageview -t stats_searchview -t stats_searchview_categories -t stats_searchview_subcategories -t stats_serviceview -t stats_serviceview_categories -t stats_serviceview_subcategories -t stats_structureview  -c | psql $DEST_DB_URL
