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
	     echo "> Dossier '$f'"
             walkDirs "$f"
        elif [ "${f##*.}" = "sql" ]; then
            echo "Exécution de '$f' sur la DB source"
  	    psql $SRC_DB_URL -q -f "$f"
	    #
	    # Nommage des fichiers : (/d+_)nom_de_table(.sql)            
	    tblname=$(basename "$f" .sql)
	    tblname=$(echo $tblname | cut -d"_" -f2-)
	    echo "Ajout de '$tblname' pour le dump vers DB destination"
	    tables_stmt+="-t $tblname "
	    
	    # Note :
	    # workaround pour permettre de détruire en avance ce qui doit être 
	    # importé sur la base cible.
	    # Pourquoi ?
	    # Les ordres DROP TABLE générés par pg_dump ne contiennent *pas* de clause CASCADE. 
	    # => les tables référencées par des vues ne peuvent pas être détruites et 
	    # recréés uniquement par le dump (seulement en détruisant et recréant la base).
	    # Des discussions pour inclure une clause spécifique --drop-cascade dans pg_dump 
	    # ont eu lieu il y quelques années, sans résultat.
	    # Solution pas très propre, mais au moins fonctionnelle 
	    # le temps d'en trouver une meilleure (ou pas).
	    echo "Suppression de '$tblname' sur la DB de destination"
	    psql -q -c "DROP TABLE $tblname CASCADE;" $DEST_DB_URL 
	    psql -q -c "DROP VIEW $tblname CASCADE;" $DEST_DB_URL 
	    
	    echo "--"
        fi
    done
    if [ -n "$tables_stmt" ]; then
	    echo "Export du dump vers la DB de destination"
	    pg_dump $SRC_DB_URL -O -c $tables_stmt | psql -q $DEST_DB_URL
	    echo "Dump exporté"
    fi
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
echo "--"
echo "Terminé!"
