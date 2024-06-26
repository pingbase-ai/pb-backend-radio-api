#!/bin/bash

set -e

if [ "$MODE" = "worker" ]; then
    exec python manage.py qcluster
else
    exec daphne --bind 0.0.0.0 master_mind.asgi:application --http-timeout 240
fi
