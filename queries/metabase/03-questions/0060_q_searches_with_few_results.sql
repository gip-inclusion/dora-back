-- Question(s) concernée(s):
--   • "Nombre de recherches aboutissant à peu de résultats (<6)"
--   • "Nombre de recherches aboutissant à 0 résultat" 

DROP TABLE IF EXISTS q_searches_with_few_results;

CREATE TABLE q_searches_with_few_results AS (
    SELECT 
        search.id AS "id",
        search.path AS "path",
        search.date AS "date",
        search.num_results AS "num_results",
        search.department AS "department",
        ss.label AS "label",
        category.label AS "category"
    FROM stats_searchview AS search
        LEFT JOIN stats_searchview_categories AS "service" ON search.id = "service".searchview_id
        LEFT JOIN services_servicecategory AS category ON "service".servicecategory_id = category.id
        LEFT JOIN structures_structuremember AS member ON search.user_id = member.user_id
        LEFT JOIN mb_structure AS structure ON member.structure_id = structure.id
        LEFT JOIN structures_structure_national_labels AS ssnl ON structure.id = ssnl.structure_id
        LEFT JOIN structures_structurenationallabel AS ss ON ssnl.structurenationallabel_id = ss.id
    WHERE 
        search.num_results < 6
        AND search.is_staff = FALSE
        AND search.is_manager = FALSE
);
