#!/bin/bash

set -e

if [ "$MODE" = "worker" ]; then
    exec  newrelic-admin run-program python manage.py qcluster
else
    exec  newrelic-admin run-program gunicorn --bind 0.0.0.0:8000 master_mind.wsgi:application --timeout 240
fi
