-- Historique des traitements de tâches de notification

-- noqa: disable=LT05

drop table if exists mb_notification_logs cascade;

create table mb_notification_logs as
select
    created_at                 as "date_creation",
    payload ->> 'taskType'     as "tache",
    payload ->> 'nbCandidates' as "nb_bandidats",
    payload ->> 'nbProcessed'  as "nb_traitees",
    payload ->> 'nbObsolete'   as "nb_obsoletes",
    payload ->> 'nbErrors'     as "nb_erreurs"
from logs_actionlog
where
    msg like 'process_notification_tasks:%'
    and level = 20;


create index mb_notification_logs_date_creation_idx on public.mb_notification_logs (
    "date_creation"
);
create index mb_notification_logs_tache_idx on public.mb_notification_logs (
    "tache"
);

comment on table mb_notification_logs is 'Historique des tâches de traitement de notification';
