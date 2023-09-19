#!/bin/bash

# Désactivation du script de début septembre
echo "Envoi des courriels de relance suspendu"
exit 0;

#
## Only run on the production app
#if [ "$ENVIRONMENT" != "production" ];then
#  echo "L'envoi des courriels de rappel de mise à jour des services ne se fait qu'en production"
#  exit 0;
#fi
#
#echo "Envoi des courriels de relance"
#python /app/manage.py send_services_reminders
