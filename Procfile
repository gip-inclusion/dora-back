web: python manage.py collectstatic; gunicorn config.wsgi --log-file -
postdeploy: python manage.py migrate
