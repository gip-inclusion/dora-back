#!/bin/bash

# Vérification de la présence du endpoint Metabase dans l'environnement 
if [ -z "$METABASE_DB_URL" ];then echo "Pas de serveur Metabase connu ; export abandonné."; exit 0; fi

# Installe la dernière version de psql 
dbclient-fetcher psql

# Installe et exporte les requêtes SQL du dossier `queries` 
tools/utils/install-sql-scripts.sh queries 

# Exporte les tables de production restantes vers Metabase
tools/utils/export-db-metabase.sh

# Synchronise le schéma de la base de données
tools/utils/sync-metabase-schemas.sh
