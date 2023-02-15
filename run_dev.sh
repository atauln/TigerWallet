#!/bin/bash
#
# This script is here ONLY for quick testing of the server
# DO NOT use this in a production level environment
# That is what gunicorn is for...

clear
podman build -t dev .
echo "---- RUNNING ----"
podman run --env-file .env -p 8080:8080 dev
