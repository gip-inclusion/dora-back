-- Question(s) concernée(s):
--   • "Nombre de vues de fiches structure"

drop table if exists q_structureviews_by_monthyear_department;

create table q_structureviews_by_monthyear_department as (
    select
        mb_user.department                    as "department",
        date_trunc('month', struct_view.date) as "period",
        count(*)                              as "count"
    from stats_structureview as struct_view
    left join mb_user on struct_view.user_id = mb_user.id
    where
        struct_view.is_structure_member = false
        and struct_view.is_structure_admin = false
        and struct_view.is_staff = false
    group by
        date_trunc('month', struct_view.date),
        mb_user.department
    order by
        date_trunc('month', struct_view.date) asc
);
