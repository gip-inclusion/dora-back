-- Question(s) concernée(s):
--   • "Vues d'un service dora avec infos de contact publiques"

drop table if exists q_serviceviews_by_monthyear_department;

create table q_serviceviews_by_monthyear_department as (
    select
        serv_view.structure_department      as "department",
        date_trunc('month', serv_view.date) as "period",
        count(*)                            as "count"
    from stats_serviceview as serv_view
    left join mb_service as serv on serv_view.service_id = serv.id
    where
        serv_view.is_logged = false
        and serv.is_contact_info_public = true
    group by
        date_trunc('month', serv_view.date),
        serv_view.structure_department
    order by
        date_trunc('month', serv_view.date) asc
);
