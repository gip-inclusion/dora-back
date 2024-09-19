-- Question(s) concernée(s):
--   • "Evolution du nombre de recherhces - avec typologie"

DROP TABLE IF EXISTS q_searches_by_monthyear_department_label;

CREATE TABLE q_searches_by_monthyear_department_label AS (
    SELECT 
        to_char(search.date, 'YYYY-MM') AS "month_year",
        search.department AS "department",
        COUNT(DISTINCT search.id) AS "count",
        ss.label AS "label"
    FROM stats_searchview AS search
        LEFT JOIN stats_searchview_categories AS "service" ON search.id = "service".searchview_id
        LEFT JOIN services_servicecategory AS category ON "service".servicecategory_id = category.id
        LEFT JOIN structures_structuremember AS member ON search.user_id = member.user_id
        LEFT JOIN mb_structure AS structure ON member.structure_id = structure.id
        LEFT JOIN structures_structure_national_labels AS ssnl ON structure.id = ssnl.structure_id
        LEFT JOIN structures_structurenationallabel AS ss ON ssnl.structurenationallabel_id = ss.id
    WHERE 
        search.is_staff = FALSE
        AND search.is_manager = FALSE
    GROUP BY
        to_char(search.date, 'YYYY-MM'),
        search.department,
        ss.label
);