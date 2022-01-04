# dora-back

## Pré-requis

- Python 3
- PostgresQL avec l'extension [PostGIS](https://postgis.net/).
- [GDAL](https://gdal.org/).

## Installation

- Créer une base de données PostgresQL `dora`.
- Renommer le dossier `envs-example` en `envs`
- Dans le fichier `envs/dev.env`, compléter la variable `POSTGRES_USER`.
- Dans le fichier `envs/secrets.env`, compléter les variables `POSTGRES_PASSWORD` et `DJANGO_SECRET_KEY`.

```bash
# Installer les dépendances
pip install -r requirements/dev.txt

# Vérifier que tout fonctionne
./manage.py check

# Créer les tables de la base de données
./manage.py migrate
```

## Développement

```bash
# Démarrer le serveur
./manage.py runserver
```

## Contribution

```bash
# Installer les hooks de pre-commit:
pre-commit install
```
