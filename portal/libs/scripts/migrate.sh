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
elegi_informarte
epubparser
dashboard
actstream"

for app in $SOUTH_APPS; do
    DJANGO_SETTINGS_MODULE="install_settings" python -W ignore manage.py migrate $app
done

exec 2>&3

