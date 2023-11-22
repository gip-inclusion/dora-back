#!/bin/bash

# A NE PAS UTILISER DIRECTEMENT (sans bonne raison) : 
# script lancé par 'update-metabase-db.sh`

export SRC_DB_URL=$DATABASE_URL
export DEST_DB_URL=$METABASE_DB_URL

function walkDirs() {
    local d="$1"
    local tables_stmt=''
    for f in "$d"/*; do
        if [ -d "$f" ]; then
             walkDirs "$f"
        elif [ "${f##*.}" = "sql" ]; then
            echo "Exécution de '$f' sur la DB source"
  	    psql $SRC_DB_URL -q -f "$f"
            # Nommage des fichiers : nnn_nom_de_table.sql            
	    tblname=$(basename "$f" .sql)
	    tblname=${tblname:4}
	    echo "Ajout de '$tblname' pour le dump vers DB destination"
	    tables_stmt+="-t $tblname "
	    echo "--"
        fi
    done
    echo "Export du dump vers la DB de destination"
    pg_dump $SRC_DB_URL -O -c --if-exists $tables_stmt | psql -q $DEST_DB_URL
    echo "--"
    echo "Terminé!"
}

if [ $# -ne 1 ]; then
    echo "Usage: $0 dir_path"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "Erreur: $1 n'est pas un répertoire valide"
    exit 1
fi

walkDirs "$1"
