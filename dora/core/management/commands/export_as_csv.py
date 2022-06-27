import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction

logging.basicConfig()
logger = logging.getLogger()


def directory(s: str) -> Path:
    path = Path(s)
    if not path.is_dir():
        raise ValueError
    return path


CREATE_SERVICES_VIEW = f"""
CREATE VIEW services_export AS (
    SELECT
        s.slug,
        s.name,
        s.short_desc AS "shortDesc",
        s.full_desc AS "fullDesc",
        k.kinds,
        c.categories,
        sc.subcategories,
        ac.access_conditions AS "accessConditions",
        cp.concerned_public AS "concernedPublic",
        s.is_cumulative AS "isCumulative",
        s.has_fee AS hasFee,
        s.fee_details AS "feeDetails",
        bam.beneficiaries_access_modes AS "beneficiariesAccessModes",
        s.beneficiaries_access_modes_other AS "beneficiariesAccessModesOther",
        com.coach_orientation_modes AS "coachOrientationModes",
        s.coach_orientation_modes_other AS "coachOrientationModesOther",
        r.requirements,
        cr.credentials,
        s.online_form AS "onlineForm",
        lk.location_kinds AS "locationKinds",
        s.remote_url AS "remoteUrl",
        s.address1,
        s.address2,
        s.postal_code AS "postalCode",
        s.city_code AS "cityCode",
        s.city,
        ST_X(ST_CENTROID(s.geom :: TEXT)) AS "longitude",
        ST_Y(ST_CENTROID(s.geom :: TEXT)) AS "latitude",
        s.diffusion_zone_type AS "diffusionZoneType",
        s.diffusion_zone_details AS "diffusionZoneDetails",
        s.qpv_or_zrr AS "qpvOrZrr",
        s.recurrence,
        s.suspension_date AS "suspensionDate",
        stru.siret AS "structure",
        cast(s.creation_date as date) AS "creationDate",
        cast(s.modification_date as date) AS "modificationDate",
        cast(s.publication_date as date) AS "publicationDate",
        concat('{settings.FRONTEND_URL}/services/', s.slug) AS "linkOnSource"
    FROM
        services_service AS s
        INNER JOIN structures_structure AS stru ON stru.id = s.structure_id
        LEFT JOIN (
            SELECT
                sk.service_id AS service_id,
                string_agg(k.label, '|') AS kinds
            FROM
                services_service_kinds AS sk
                INNER JOIN services_servicekind AS k ON k.id = sk.servicekind_id
            GROUP BY
                sk.service_id
        ) AS k ON k.service_id = s.id
        LEFT JOIN (
            SELECT
                sc.service_id AS service_id,
                string_agg(c.label, '|') AS categories
            FROM
                services_service_categories AS sc
                INNER JOIN services_servicecategory AS c ON c.id = sc.servicecategory_id
            GROUP BY
                sc.service_id
        ) AS c ON c.service_id = s.id
        LEFT JOIN (
            SELECT
                ssc.service_id AS service_id,
                string_agg(sc.label, '|') AS subcategories
            FROM
                services_service_subcategories AS ssc
                INNER JOIN services_servicesubcategory AS sc ON sc.id = ssc.servicesubcategory_id
            GROUP BY
                ssc.service_id
        ) AS sc ON sc.service_id = s.id
        LEFT JOIN (
            SELECT
                sac.service_id AS service_id,
                string_agg(ac.name, '|') AS access_conditions
            FROM
                services_service_access_conditions AS sac
                INNER JOIN services_accesscondition AS ac ON ac.id = sac.accesscondition_id
            GROUP BY
                sac.service_id
        ) AS ac ON ac.service_id = s.id
        LEFT JOIN (
            SELECT
                scp.service_id AS service_id,
                string_agg(cp.name, '|') AS concerned_public
            FROM
                services_service_concerned_public AS scp
                INNER JOIN services_concernedpublic AS cp ON cp.id = scp.concernedpublic_id
            GROUP BY
                scp.service_id
        ) AS cp ON cp.service_id = s.id
        LEFT JOIN (
            SELECT
                sbam.service_id AS service_id,
                string_agg(bam.label, '|') AS beneficiaries_access_modes
            FROM
                services_service_beneficiaries_access_modes AS sbam
                INNER JOIN services_beneficiaryaccessmode AS bam ON bam.id = sbam.beneficiaryaccessmode_id
            GROUP BY
                sbam.service_id
        ) AS bam ON bam.service_id = s.id
        LEFT JOIN (
            SELECT
                scom.service_id AS service_id,
                string_agg(com.label, '|') AS coach_orientation_modes
            FROM
                services_service_coach_orientation_modes AS scom
                INNER JOIN services_coachorientationmode AS com ON com.id = scom.coachorientationmode_id
            GROUP BY
                scom.service_id
        ) AS com ON com.service_id = s.id
        LEFT JOIN (
            SELECT
                sr.service_id AS service_id,
                string_agg(r.name, '|') AS requirements
            FROM
                services_service_requirements AS sr
                INNER JOIN services_requirement AS r ON r.id = sr.requirement_id
            GROUP BY
                sr.service_id
        ) AS r ON r.service_id = s.id
        LEFT JOIN (
            SELECT
                scr.service_id AS service_id,
                string_agg(cr.name, '|') AS credentials
            FROM
                services_service_credentials AS scr
                INNER JOIN services_credential AS cr ON cr.id = scr.credential_id
            GROUP BY
                scr.service_id
        ) AS cr ON cr.service_id = s.id
        LEFT JOIN (
            SELECT
                slk.service_id AS service_id,
                string_agg(lk.label, '|') AS location_kinds
            FROM
                services_service_location_kinds AS slk
                INNER JOIN services_locationkind AS lk ON lk.id = slk.locationkind_id
            GROUP BY
                slk.service_id
        ) AS lk ON lk.service_id = s.id
        WHERE s.status='PUBLISHED'
);
"""


class Command(BaseCommand):
    """Commande d'export des structures et des services sous format csv

    Usage: `python manage.py export_as_csv /tmp/`
    """

    def add_arguments(self, parser):
        parser.add_argument("output_dir", type=directory)

    def handle(self, *args, **options):
        structures_output_path = options["output_dir"] / "structures.csv"
        services_output_path = options["output_dir"] / "services.csv"

        with transaction.atomic():
            with connection.cursor() as cursor:
                # export des structures
                cursor.execute(
                    f"""
                    CREATE VIEW structures_export As (
                        SELECT
                            s.slug,
                            s.name,
                            s.siret,
                            s.code_safir_pe,
                            t.value AS "typology",
                            s.short_desc AS "shortDesc",
                            s.full_desc AS "fullDesc",
                            s.url,
                            s.email,
                            s.phone,
                            s.postal_code AS "postalCode",
                            s.city_code AS "cityCode",
                            s.city,
                            s.department,
                            s.address1,
                            s.address2,
                            s.ape,
                            s.longitude,
                            s.latitude,
                            cast(s.creation_date as date) AS "creationDate",
                            cast(s.modification_date as date) AS "modificationDate",
                            ss.value AS "source",
                            concat('{settings.FRONTEND_URL}/structures/', s.slug) AS "linkOnSource"
                        FROM
                            structures_structure AS s
                            LEFT JOIN structures_structuretypology AS t ON s.typology_id = t.id
                            LEFT JOIN structures_structuresource AS ss ON s.source_id = ss.id
                    );"""
                )
                with structures_output_path.open("w") as f:
                    cursor.copy_expert(
                        "COPY (SELECT * FROM structures_export) TO STDOUT WITH CSV HEADER",
                        f,
                    )
                cursor.execute("DROP VIEW structures_export;")

                # export des services
                cursor.execute(CREATE_SERVICES_VIEW)
                with services_output_path.open("w") as f:
                    cursor.copy_expert(
                        "COPY (SELECT * FROM services_export) TO STDOUT WITH CSV HEADER",
                        f,
                    )
                cursor.execute("DROP VIEW services_export;")
