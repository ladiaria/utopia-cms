# coding:utf8
"""
utopia-cms, 2018-2022, Aníbal Pacheco

Global variables definition, to avoid its definition multiple times inside the apps modules.

TODO: if mongo server fails after this global vars are set, the global client instances in views will start to fail.
      Change this "global" approach asap to a more robust approach, for example, a function that returns a new mongo
      client instance (or checks for the connectivity on the global instance and returns it if ok).
"""
from __future__ import unicode_literals
import csv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from django.conf import settings


# mongodb database
try:
    connect, timeout = getattr(settings, 'MONGODB_CONNECT_AT_CLIENT_CREATION', True), 1000
    client = MongoClient(serverSelectionTimeoutMS=timeout)
    client.server_info()
    if not connect:
        client = MongoClient(serverSelectionTimeoutMS=timeout, connect=False)
    global mongo_db
    mongo_db = client[settings.MONGODB_DATABASE] if settings.MONGODB_DATABASE else None
except ServerSelectionTimeoutError:
    mongo_db = None

# blacklisted emails
global blacklisted
blacklisted = set(
    [row[0] for row in csv.reader(open(settings.CORE_NEWSLETTER_BLACKLIST))]
) if hasattr(settings, 'CORE_NEWSLETTER_BLACKLIST') else set()
