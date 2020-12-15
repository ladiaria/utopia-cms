#!/bin/sh

cd /srv/code/ldsite

find ./ -type d -exec chmod 2775 \{\} \;
find ./ -type f -exec chmod 0664 \{\} \;
chown -R apache:sysDevel ./
chmod ug+x ./bin/* ./portal/manage.py ./portal/bin/*
chmod 777 ./cache # este es para produccion
