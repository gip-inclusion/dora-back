#!/bin/bash

# Exécution seulement sur l'environnement de production 
if [ "$ENVIRONMENT" != "production" ];then exit 0; fi

# Vérification de la présence du endpoint Metabase dans l'environnement 
if [ -z "$METABASE_DB_URL" ];then echo "Pas de serveur Metabase connu ; export abandonné."; exit 0; fi

# Installe la dernière version de psql 
dbclient-fetcher psql

# Installe et exporte les requêtes SQL du dossier `queries` 
tools/lib/install-sql-scripts.sh queries 

# Exporte les tables de production restantes vers Metabase
tools/lib/export-db-metabase.sh
