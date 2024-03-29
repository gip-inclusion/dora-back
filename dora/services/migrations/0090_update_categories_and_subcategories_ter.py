# Generated by Django 4.0.6 on 2022-08-17 12:57

from django.db import migrations

from dora.services.migration_utils import update_subcategory_value_and_label


def migrate_services_options(apps, schema_editor):
    ServiceSubCategory = apps.get_model("services", "ServiceSubCategory")

    update_subcategory_value_and_label(
        ServiceSubCategory,
        "mobilite--accompagnement-parcours-mobilite",
        "mobilite--etre-accompagne-dans-son-parcours-mobilite",
        "Être accompagné(e) dans son parcours mobilité",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "mobilite--preparer-permis",
        "mobilite--preparer-son-permis-de-conduire-se-reentrainer-a-la-conduite",
        "Préparer son permis de conduire, se réentraîner à la conduite",
    )

    update_subcategory_value_and_label(
        ServiceSubCategory,
        "preparer-sa-candidature--realiser-un-cv-etou-une-lettre-de-motivation",
        "preparer-sa-candidature--realiser-un-cv-et-ou-une-lettre-de-motivation",
        "Réaliser un CV et/ou une lettre de motivation",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "mobilite--entretenir-vehicule",
        "mobilite--entretenir-reparer-son-vehicule",
        "Entretenir ou réparer son véhicule",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "mobilite--aides-a-la-reprise-d-emploi-ou-a-la-formation",
        "mobilite--aides-a-la-reprise-demploi-ou-a-la-formation",
        "Aides à la reprise d‘emploi ou à la formation",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "mobilite--louer-un-vehicule-voiture-velo-scooter",
        "mobilite--louer-un-vehicule",
        "Louer un véhicule (voiture, vélo, scooter…)",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "accompagnement-social-et-professionnel-personnalise--parcours-insertion-sociopro",
        "accompagnement-social-et-professionnel-personnalise--parcours-d-insertion-socioprofessionnel",
        "Parcours d’insertion socio-professionnel",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "remobilisation--restaurer-confiance",
        "remobilisation--restaurer-sa-confiance-son-image-de-soi",
        "Restaurer sa confiance, son image de soi",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "remobilisation--identifier-competences",
        "remobilisation--identifier-ses-competences-et-aptitudes",
        "Identifier ses compétences et aptitudes",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "acces-aux-droits-et-citoyennete--accompagnement-demarches-admin",
        "acces-aux-droits-et-citoyennete--accompagnement-dans-les-demarches-administratives",
        "Accompagnement dans les démarches administratives",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "accompagnement-social-et-professionnel-personnalise--definition-projet-pro",
        "accompagnement-social-et-professionnel-personnalise--definition-du-projet-professionnel",
        "Définition du projet professionnel",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "mobilite--utiliser-deux-roues",
        "mobilite--apprendre-a-utiliser-un-deux-roues",
        "Apprendre à utiliser un deux roues",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "acces-aux-droits-et-citoyennete--connaitre-droits",
        "acces-aux-droits-et-citoyennete--connaitre-ses-droits",
        "Connaitre ses droits",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "handicap--retour-maintien-emploi",
        "handicap--favoriser-le-retour-et-le-maintien-dans-lemploi",
        "Favoriser le retour et le maintien dans l’emploi",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "logement-hebergement--acommpagnement-logement",
        "logement-hebergement--etre-accompagne-pour-se-loger",
        "Être accompagné(e) pour se loger",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "gestion-financiere--accompagnement-difficultes-financieres",
        "gestion-financiere--accompagnement-aux-personnes-en-difficultes-financieres",
        "Accompagnement aux personnes en difficultés financières",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "handicap--accompagnement-structure-specialisee",
        "handicap--accompagnement-par-une-structure-specialisee",
        "Accompagnement par une structure spécialisée",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "famille--garde-enfants",
        "famille--garde-denfants",
        "Garde d'enfants",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "logement-hebergement--probleme-logement",
        "logement-hebergement--probleme-avec-son-logement",
        "Problème avec son logement",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "handicap--connaissance-droits-travailleurs",
        "handicap--connaissance-des-droits-des-travailleurs",
        "Connaissance des droits des travailleurs",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "famille--accompagnement-parents",
        "famille--information-et-accompagnement-des-parents",
        "Information et accompagnement des parents",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "famille--soutien-familles",
        "famille--soutien-aux-familles",
        "Soutien aux familles",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "handicap--faire-reconnaitre-handicap",
        "handicap--faire-reconnaitre-un-handicap",
        "Faire reconnaitre un handicap",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "handicap--adaptation-poste-travail",
        "handicap--adaptation-au-poste-de-travail",
        "Adaptation au poste de travail",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "sante--soin-prevention-maladie",
        "sante--se-soigner-et-prevenir-la-maladie",
        "Se soigner et prévenir la maladie",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "sante--diagnostic-et-accompagnement-a-l-employabilite",
        "sante--diagnostic-et-accompagnement-a-lemployabilite",
        "Se soigner et prévenir la maladie",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "gestion-financiere--gerer-budget",
        "gestion-financiere--apprendre-a-gerer-son-budget",
        "Apprendre à gérer son budget",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "gestion-financiere--beneficier-d-aides-financieres",
        "gestion-financiere--beneficier-daides-financieres",
        "Bénéficier d‘aides financières",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "sante--bien-etre-psy",
        "sante--bien-etre-psychologique",
        "Bien être psychologique",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "gestion-financiere--prevention-et-gestion-surendettement",
        "gestion-financiere--prevention-et-gestion-du-surendettement",
        "Prévention et gestion du surendettement",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "logement-hebergement--reprendre-emploi-formation",
        "logement-hebergement--reprendre-un-emploi-ou-une-formation",
        "Reprendre un emploi ou une formation",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "numerique--soutenir-la-parentalite-et-leducation-avec-le-numerique",
        "numerique--soutenir-la-parentalite-et-l-education-avec-le-numerique",
        "Soutenir la parentalité et l’éducation avec le numérique",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "sante--addiction",
        "sante--faire-face-a-une-situation-daddiction",
        "Faire face à une situation d’addiction",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "sante--prise-en-charge-frais-medicaux",
        "sante--obtenir-la-prise-en-charge-de-frais-medicaux",
        "Obtenir la prise en charge de frais médicaux",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "equipement-et-alimentation--acces-materiel-informatique",
        "equipement-et-alimentation--acces-a-du-materiel-informatique",
        "Accès à du matériel informatique",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "numerique--sequiper-en-materiel-informatique",
        "numerique--s-equiper-en-materiel-informatique",
        "S’équiper en matériel informatique",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "famille--jeune-sans-soutien-familial",
        "famille--jeunes-sans-soutien-familial",
        "Jeunes sans soutien familial",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "logement-hebergement--adapter-logement",
        "logement-hebergement--besoin-dadapter-mon-logement",
        "Besoin d’adapter mon logement",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "logement-hebergement--mal-loge-sans-logis",
        "logement-hebergement--mal-loges-sans-logis",
        "Mal logé/sans logis",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "gestion-financiere--utilisation-compte-bancaire",
        "gestion-financiere--creation-et-utilisation-dun-compte-bancaire",
        "Création et utilisation d‘un compte bancaire",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "acces-aux-droits-et-citoyennete--demandeurs-asile-naturalisation",
        "acces-aux-droits-et-citoyennete--demandeurs-dasile-et-naturalisation",
        "Demandeurs d’asile et naturalisation",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "equipement-et-alimentation--acces-telephone",
        "equipement-et-alimentation--acces-a-un-telephone-et-un-abonnement",
        "Accès à un téléphone et un abonnement",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "handicap--adapter-logement",
        "handicap--adapter-son-logement",
        "Adapter son logement",
    )
    update_subcategory_value_and_label(
        ServiceSubCategory,
        "logement-hebergement--adapter-logement",
        "logement-hebergement--besoin-dadapter-mon-logement",
        "Besoin d’adapter mon logement",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0089_update_categories_and_subcategories_bis"),
    ]

    operations = [
        migrations.RunPython(
            migrate_services_options, reverse_code=migrations.RunPython.noop
        ),
    ]
