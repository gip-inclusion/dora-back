# Generated by Django 4.0.6 on 2022-08-03 08:41

from django.db import migrations

"""
# Création d'activité
- "creation-activite--demarrer-activite" => "creation-activite--structurer-son-projet-de-creation-dentreprise"
- "creation-activite--elaborer-projet" => "creation-activite--structurer-son-projet-de-creation-dentreprise"
- "creation-activite--de-lidee-au-projet" => "creation-activite--definir-son-projet-de-creation-dentreprise"

# Numérique
- "numerique--accompagner-enfant" => "numerique--autre"
- "numerique--connaitre-env-numerique" => "numerique--approfondir-ma-culture-numerique"
- "numerique--prendre-en-main-equipement-informatique" => "numerique--prendre-en-main-un-ordinateur"
- "numerique--realiser-demarche-en-ligne" => "numerique--gagner-en-autonomie-dans-les-demarches-administratives"
- "numerique--trouver-emploi-formation" => "numerique--favoriser-mon-insertion-professionnelle"
- "numerique--utiliser-smartphone" => "numerique--prendre-en-main-un-smartphone-ou-une-tablette"

- "numerique--creer-gerer-contenus-numeriques" => "numerique--utiliser-le-numerique-au-quotidien"
- "numerique--echanger-avec-proches" => "numerique--utiliser-le-numerique-au-quotidien"
- "numerique--naviguer-internet" => "numerique--utiliser-le-numerique-au-quotidien"
- "numerique--usage-courriels" => "numerique--utiliser-le-numerique-au-quotidien"
- "numerique--bases-traitement-texte" => "numerique--utiliser-le-numerique-au-quotidien"

# Emplois
- Rattacher les services liés au besoin "emploi--choisir-metier" à la thématique "emploi-choisir-metier"
- Rattacher les services liés au besoin "emploi--preparer-candidature" à la thématique "emploi-preparer-sa-candidature"
- Rattacher les services liés au besoin "emploi--trouver-emploi" à la thématique "emploi-trouver-emploi"

- Délier la thématique "emploi"
- Délier tous les besoins "emploi--*"
"""

SUBSTITUTIONS = {
    "creation-activite--demarrer-activite": "creation-activite--structurer-son-projet-de-creation-dentreprise",
    "creation-activite--elaborer-projet": "creation-activite--structurer-son-projet-de-creation-dentreprise",
    "creation-activite--de-lidee-au-projet": "creation-activite--definir-son-projet-de-creation-dentreprise",
    "numerique--accompagner-enfant": "numerique--autre",
    "numerique--connaitre-env-numerique": "numerique--approfondir-ma-culture-numerique",
    "numerique--prendre-en-main-equipement-informatique": "numerique--prendre-en-main-un-ordinateur",
    "numerique--realiser-demarche-en-ligne": "numerique--gagner-en-autonomie-dans-les-demarches-administratives",
    "numerique--trouver-emploi-formation": "numerique--favoriser-mon-insertion-professionnelle",
    "numerique--utiliser-smartphone": "numerique--prendre-en-main-un-smartphone-ou-une-tablette",
    "numerique--creer-gerer-contenus-numeriques": "numerique--utiliser-le-numerique-au-quotidien",
    "numerique--echanger-avec-proches": "numerique--utiliser-le-numerique-au-quotidien",
    "numerique--naviguer-internet": "numerique--utiliser-le-numerique-au-quotidien",
    "numerique--usage-courriels": "numerique--utiliser-le-numerique-au-quotidien",
    "numerique--bases-traitement-texte": "numerique--utiliser-le-numerique-au-quotidien",
}


def migrate_cats_subcats(apps, schema_editor):
    ServiceSuggestion = apps.get_model("service_suggestions", "ServiceSuggestion")
    for s in ServiceSuggestion.objects.all():
        cats = list(s.contents["categories"])
        subcats = list(s.contents["subcategories"])

        # Substitutions simples
        subcats = list(set(SUBSTITUTIONS.get(value, value) for value in subcats))

        # Emplois: subcat => cat
        if "emploi--choisir-metier" in subcats:
            cats.append("emploi-choisir-metier")
        if "emploi--preparer-candidature" in subcats:
            cats.append("emploi-preparer-sa-candidature")
        if "emploi--trouver-emploi" in subcats:
            cats.append("emploi-trouver-emploi")
        cats = list(set(cats))

        # Délier emploi
        cats = [val for val in cats if val != "emploi"]
        # Délier les besoins emploi
        subcats = [val for val in subcats if not val.startswith("emploi--")]

        # print("###")
        # print(sorted(s.contents["categories"]))
        # print(sorted(cats))
        # print("---")
        # print(sorted(s.contents["subcategories"]))
        # print(sorted(subcats))
        s.contents["categories"] = cats
        s.contents["subcategories"] = subcats
        s.save(update_fields=["contents"])


class Migration(migrations.Migration):

    dependencies = [
        ("service_suggestions", "0003_rename_ids"),
    ]

    operations = [
        migrations.RunPython(
            migrate_cats_subcats, reverse_code=migrations.RunPython.noop
        ),
    ]
