# coding:utf-8
"""
utopia-cms, 2018-2024, Aníbal Pacheco, utopia-cms.

Global variables definition, to avoid its definition multiple times inside the apps modules.

TODO: 1. if mongo server fails after this global vars are set, the global client instances in views will start to fail.
      Change this "global" approach asap to a more robust approach, for example, a function that returns a new mongo
      client instance (or checks for the connectivity on the global instance and returns it if ok).
      Also some checks "if mongo_db is not None" are missing in some views (adzone.views for example).
      2. Determine when MONGODB_CONNECT_AT_CLIENT_CREATION must be False, on newer deployments we saw that this value
      must be set to False to avoid a "pool" error exception. (RHEL7/9-Mongod7).
"""

import csv
import json
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from django.conf import settings


# mongodb database
try:
    connect, timeout = getattr(settings, 'MONGODB_CONNECT_AT_CLIENT_CREATION', True), 1000
    connection_string = getattr(settings, 'MONGODB_CONNECTION_STRING', None)
    connection_args = (connection_string, ) if connection_string else ()
    client = MongoClient(*connection_args, serverSelectionTimeoutMS=timeout)
    client.server_info()
    if not connect:
        client = MongoClient(*connection_args, serverSelectionTimeoutMS=timeout, connect=False)
    global mongo_db
    mongo_db = client[settings.MONGODB_DATABASE] if settings.MONGODB_DATABASE else None
except ServerSelectionTimeoutError:
    mongo_db = None

# two email block lists (bounces in last 7 days, and bounces max ammount reached)
global blocklisted, bouncer_blocklisted
blocklisted, bouncer_blocklisted = [
    (
        set(
            [row[0] for row in csv.reader(open(getattr(settings, csv_setting)))]
        ) if hasattr(settings, csv_setting) else set()
    ) for csv_setting in ('CORE_NEWSLETTER_BLOCKLIST', "THEDAILY_EMAILBOUNCE_MAX_REACHED_CSV")
]


def whitelisted_domains(update_list=None):
    dlist_json = getattr(settings, "THEDAILY_DOMAIN_WHITELIST_JSON", None)
    if not dlist_json:
        return []
    if update_list is None:
        fobj = open(dlist_json)
        dlist = json.loads(fobj.read()).get("domains", [])
        fobj.close()
        return dlist
    else:
        fobj = open(dlist_json, "w")
        fobj.write(json.dumps({"domains": update_list}))
        fobj.close()
