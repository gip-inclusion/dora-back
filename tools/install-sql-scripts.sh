#!/bin/bash

# Only run on the local app (for now)
if [ "$ENVIRONMENT" != "local" ];then exit 0; fi

# Install the latest psql client
# dbclient-fetcher psql

# TODO: Discussion : put in on source and dump it, or directly on target (metabase)
# target directly metabase for now ...
export SRC_DB_URL=$DATABASE_URL
export DEST_DB_URL=$METABASE_DB_URL

function walkDirs() {
    local d="$1"
    for f in "$d"/*; do
        if [ -d "$f" ]; then
             walkDirs "$f"
        elif [ "${f##*.}" = "sql" ]; then
            echo "Installing: $f"
  	    psql $DEST_DB_URL -f "$f"
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
