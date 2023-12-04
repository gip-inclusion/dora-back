#!/bin/bash

# A NE PAS UTILISER DIRECTEMENT (sans bonne raison) : 
# script lancé par 'update-metabase-db.sh`

export DEST_DB_URL=$METABASE_DB_URL

# Export des tables vers METABASE
pg_dump $DATABASE_URL -O -c --if-exists -t orientations_* -t stats_*  -t structures_* -t services_servicesource -t services_bookmark -t services_servicefee -t services_accesscondition -t services_beneficiaryaccessmode -t services_coachorientationmode -t services_concernedpublic -t services_credential -t services_locationkind -t services_requirement -t services_service_access_conditions -t services_service_beneficiaries_access_modes -t services_service_categories -t services_service_coach_orientation_modes -t services_service_concerned_public -t services_service_credentials -t services_service_kinds -t services_service_location_kinds -t services_service_requirements -t services_service_subcategories -t services_servicecategory -t services_servicekind -t services_servicemodificationhistoryitem -t services_servicestatushistoryitem -t services_servicesubcategory | psql -q $DEST_DB_URL
