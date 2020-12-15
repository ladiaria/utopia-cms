#!/bin/sh

. activate.sh

cd ../portal

./manage.py runserver 0.0.0.0:9500
