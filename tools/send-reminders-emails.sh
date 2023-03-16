#!/bin/bash

# Only run on the production app
if [ "$ENVIRONMENT" != "production" ];then
  echo "L'envoi des courriels de rappel de mise à jour des services ne se fait qu'en production"
  exit 0;
fi

python /app/manage.py send_services_update_reminders -n
