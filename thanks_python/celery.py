from celery import Celery, bootsteps
from contributions.tasks import setup_cpython_repo, update_database_objects

import os
import logging

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thanks_python.settings")

app = Celery("thanks_python")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


class InitRepoStep(bootsteps.StartStopStep):
    def start(self, c):
        logging.info("Initialize the repository.")
        setup_cpython_repo()
        update_database_objects()


app.steps["worker"].add(InitRepoStep)
