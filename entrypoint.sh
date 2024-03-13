#!/bin/bash

set -e

if [ "$MODE" = "worker" ]; then
    exec python manage.py qcluster
else
    exec gunicorn --bind 0.0.0.0:8000 master_mind.wsgi:application --timeout 240
fi
