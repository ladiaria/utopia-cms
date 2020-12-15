#!/bin/sh
# Sincroniza algunos recursos que no estan trackeados en bazaar

rsync -az --progress ladiaria.com:/srv/ladiaria/portal/media/photologue ../portal/media/photologue/
