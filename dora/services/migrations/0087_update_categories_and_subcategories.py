# Generated by Django 4.0.6 on 2022-08-17 12:57

from django.db import migrations

from dora.services.migration_utils import (
    add_categories_and_subcategories_if_subcategory,
    create_subcategory,
    update_category_value_and_label,
    update_subcategory_value_and_label,
)


def migrate_services_options(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    ServiceCategory = apps.get_model("services", "ServiceCategory")
    ServiceSubCategory = apps.get_model("services", "ServiceSubCategory")

    # Accès aux droits & citoyenneté
    create_subcategory(
        ServiceSubCategory,
        value="acces-aux-droits--developpement-durable",
        label="Développement durable",
    )
    create_subcategory(
        ServiceSubCategory,
        value="acces-aux-droits--faciliter-laction-citoyenne",
        label="Faciliter l‘action citoyenne",
    )

    # Acco. global individualisé => Accompagnement social et professionnel personnalisé
    update_category_value_and_label(
        ServiceCategory,
        old_value="acc-global-indiv",
        new_value="accompagnement-social-et-professionnel-personnalise",
        new_label="Accompagnement social et professionnel personnalisé",
    )

    # Création d‘activité
    create_subcategory(
        ServiceSubCategory,
        value="creation-activite--developper-son-entreprise",
        label="Développer son entreprise",
    )

    # Difficultes financières => Gestion financière
    difficultes_financiere = "difficultes-financieres"
    gestion_financiere = "gestion-financiere"

    update_category_value_and_label(
        ServiceCategory,
        old_value=difficultes_financiere,
        new_value=gestion_financiere,
        new_label="Gestion financière",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        f"{difficultes_financiere}--utilisation-compte-bancaire"
        f"{gestion_financiere}--utilisation-compte-bancaire",
        "Création et utilisation d‘un compte bancaire",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        f"{difficultes_financiere}--gerer-budget",
        f"{gestion_financiere}--gerer-budget",
        "Apprendre à gérer son budget",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        f"{difficultes_financiere}--prevention-surendettement",
        f"{gestion_financiere}--prevention-et-gestion-surendettement",
        "Prévention et gestion du surendettement",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        f"{difficultes_financiere}--accompagnement-difficultes-financieres",
        f"{gestion_financiere}--accompagnement-difficultes-financieres",
        "Accompagnement aux personnes en difficultés financières",
    )
    create_subcategory(
        ServiceSubCategory,
        f"{gestion_financiere}--acces-au-micro-credit",
        "Accès au micro-crédit",
    )
    create_subcategory(
        ServiceSubCategory,
        f"{gestion_financiere}--obtenir-une-aide-alimentaire",
        "Obtenir une aide alimentaire",
    )
    create_subcategory(
        ServiceSubCategory,
        f"{gestion_financiere}--beneficier-d-aides-financieres",
        "Bénéficier d‘aides financières",
    )

    # Famille
    create_subcategory(
        ServiceSubCategory,
        "famille--accompagnement-femme-enceinte-bebe-jeune-enfant",
        "Accompagnement de la femme enceinte, du bébé et du jeune enfant",
    )
    create_subcategory(
        ServiceSubCategory,
        "famille--soutien-a-la-parentalite",
        "Soutien à la parentalité",
    )

    # Handicap
    create_subcategory(
        ServiceSubCategory,
        "handicap--mobilite-des-personnes-en-situation-de-handicap",
        "Mobilité des personnes en situation de handicap",
    )

    # Logement et hébergement
    create_subcategory(
        ServiceSubCategory,
        "logement-hebergement--gerer-son-budget",
        "Gérer son budget",
    )
    create_subcategory(
        ServiceSubCategory,
        "logement-hebergement--connaissance-de-ses-droits-et-interlocuteurs",
        "Connaissance de ses droits et interlocuteurs",
    )

    # Mobilité
    update_subcategory_value_and_label(
        ServiceSubCategory,
        old_value="mobilite--louer-acheter-vehicule",
        new_value="mobilite--acheter-un-vehicule-motorise",
        new_label="Acheter un véhicule motorisé",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        old_value="mobilite--se-deplacer-sans-permis-ou-vehicule",
        new_value="mobilite--comprendre-et-utiliser-les-transports-en-commun",
        new_label="Comprendre et utiliser les transports en commun",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        old_value="mobilite--reprendre-emploi-formation",
        new_value="mobilite--aides-a-la-reprise-d-emploi-ou-a-la-formation",
        new_label="Aides à la reprise d‘emploi ou à la formation",
    )
    create_subcategory(
        ServiceSubCategory,
        "mobilite--acheter-un-velo",
        "Acheter un vélo",
    )
    create_subcategory(
        ServiceSubCategory,
        "mobilite--louer-un-vehicule-voiture-velo-scooter",
        "Louer un véhicule (voiture, vélo, scooter…)",
    )
    add_categories_and_subcategories_if_subcategory(
        ServiceCategory,
        ServiceSubCategory,
        Service,
        categories_value_to_add=[],
        subcategory_value_to_add=[
            "mobilite--acheter-un-velo",
            "mobilite--louer-un-vehicule-voiture-velo-scooter",
        ],
        if_subcategory_value="mobilite--acheter-un-vehicule-motorise",
    )

    # Remobilisation
    create_subcategory(
        ServiceSubCategory,
        "remobilisation--pression-sociale",
        "Pression sociale",
    )
    create_subcategory(
        ServiceSubCategory,
        "remobilisation--discrimination",
        "Discrimination",
    )
    create_subcategory(
        ServiceSubCategory,
        "remobilisation--decouvrir-son-potentiel-via-le-sport-et-la-culture",
        "Découvrir son potentiel via le sport et la culture",
    )
    create_subcategory(
        ServiceSubCategory,
        "remobilisation--participer-a-des-actions-solidaires-ou-de-benevolat",
        "Participer à des actions solidaires ou de bénévolat",
    )

    # Santé
    create_subcategory(
        ServiceSubCategory,
        "sante--accompagnement-de-la-femme-enceinte-du-bebe-et-du-jeune-enfant",
        "Accompagnement de la femme enceinte, du bébé et du jeune enfant",
    )
    create_subcategory(
        ServiceSubCategory,
        "sante--accompagner-les-traumatismes",
        "Accompagner les traumatismes",
    )
    create_subcategory(
        ServiceSubCategory,
        "sante--diagnostic-et-accompagnement-a-l-employabilite",
        "Diagnostic et accompagnement à l‘employabilité",
    )
    create_subcategory(
        ServiceSubCategory,
        "sante--prevention-et-acces-aux-soins",
        "Prévention et accès aux soins (vaccination, éducation à la santé, lutte contre la tuberculose…)",
    )
    create_subcategory(
        ServiceSubCategory,
        "sante--vie-relationnelle-et-affective",
        "Vie relationnelle et affective, dépistage et prévention des IST/VIH…",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0086_remove_service_can_update_categories_and_more"),
    ]

    operations = [
        migrations.RunPython(
            migrate_services_options, reverse_code=migrations.RunPython.noop
        ),
    ]
