-- Question(s) concernée(s):
--   • "Nombre de mobilisations par thématique"

DROP TABLE IF EXISTS q_mobilisations_by_category_department;

CREATE TABLE q_mobilisations_by_category_department AS (
    SELECT 
        mobilisation.id AS "id",
        mobilisation.path AS "path",
        mobilisation.date AS "date",
        structure.department AS "department",
        ss.label AS "label",
        category.label AS "category"
    FROM stats_mobilisationevent AS mobilisation
        LEFT JOIN services_service_categories AS "service" ON mobilisation.service_id = "service".service_id
        LEFT JOIN services_servicecategory AS category ON "service".servicecategory_id = category.id
        LEFT JOIN structures_structuremember AS member ON mobilisation.user_id = member.user_id
        LEFT JOIN mb_structure AS structure ON member.structure_id = structure.id
        LEFT JOIN structures_structure_national_labels AS ssnl ON structure.id = ssnl.structure_id
        LEFT JOIN structures_structurenationallabel AS ss ON ssnl.structurenationallabel_id = ss.id
    WHERE 
        mobilisation.is_staff = FALSE
        AND mobilisation.is_manager = FALSE
        AND mobilisation.is_structure_member = FALSE
        AND mobilisation.is_structure_admin = FALSE
);
