web: gunicorn config.wsgi:application
worker: celery worker --app=thanks_python.taskapp --loglevel=debug --beat
