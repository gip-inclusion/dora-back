-- Question(s) concernée(s):
--   • "Recherches sur les 30 derniers jours"

DROP TABLE IF EXISTS q_searches_on_last_30_days;

CREATE TABLE q_searches_on_last_30_days AS (
    SELECT 
        search.id AS "id",
        search.path AS "path",
        search.date AS "date",
        search.num_results AS "num_results",
        search.department AS "department",
        ss.label AS "label"
    FROM stats_searchview AS search
        LEFT JOIN stats_searchview_categories AS category ON search.id = category.searchview_id
        LEFT JOIN services_servicecategory AS thematique ON category.servicecategory_id = thematique.id
        LEFT JOIN structures_structuremember AS member ON search.user_id = member.user_id
        LEFT JOIN mb_structure AS structure ON member.structure_id = structure.id
        LEFT JOIN structures_structure_national_labels AS ssnl ON structure.id = ssnl.structure_id
        LEFT JOIN structures_structurenationallabel AS ss ON ssnl.structurenationallabel_id = ss.id
    WHERE 
        search.date >= NOW() - INTERVAL '30 days'
        AND search.is_staff = FALSE
        AND search.is_manager = FALSE
);
