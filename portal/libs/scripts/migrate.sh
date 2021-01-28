#!/bin/bash

exec 3>&2
exec 2> /dev/null

SOUTH_APPS="core
home
thedaily
videologue
adzone
photologue
photologue_ladiaria
signupwall
cartelera
comunidad
djangoratings
updown
epubparser
dashboard"

for app in $SOUTH_APPS; do
    DJANGO_SETTINGS_MODULE="install_settings" python -W ignore manage.py migrate $app
done

exec 2>&3

python -W ignore manage.py utopiacms_photosizes
