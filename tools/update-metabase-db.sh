#!/bin/bash

# Only run on the production app
if [ "$ENVIRONMENT" != "production" ];then exit 0; fi

# Check for Metabase endpoint
if [ -z "$METABASE_DB_URL" ];then echo "Pas de serveur Metabase connu ; export abandonnée."; exit 0; fi

# Install the latest psql client
dbclient-fetcher psql

# Install SQL queries in folder `queries`
tools/install-sql-scripts.sh queries 

# Export remaining prod tables to METABASE
tools/export-db-metabase.sh
