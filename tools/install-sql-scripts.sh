#!/bin/bash

# Only run on the local app (for now)
if [ "$ENVIRONMENT" != "production" ];then exit 0; fi

# DO NOT USE DIRECTLY (unless you know what you're doing)
# This script is launched by `update-metabase-db.sh`

export SRC_DB_URL=$DATABASE_URL
export DEST_DB_URL=$METABASE_DB_URL

function walkDirs() {
    local d="$1"
    for f in "$d"/*; do
        if [ -d "$f" ]; then
             walkDirs "$f"
        elif [ "${f##*.}" = "sql" ]; then
            echo "Installing: '$f' on source DB"
  	    psql $SRC_DB_URL -f "$f"
            
	    tblname=$(basename "$f" .sql)
	    echo "Dumping and exporting table: '$tblname' on destination DB"
	    pg_dump $SRC_DB_URL -O -t "$tblname" -c | psql $DEST_DB_URL
        fi
    done
}

if [ $# -ne 1 ]; then
    echo "Usage: $0 dir_path"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "Error: $1 is not a valid directory"
    exit 1
fi

walkDirs "$1"
