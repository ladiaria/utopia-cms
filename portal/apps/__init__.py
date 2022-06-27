# coding:utf8
"""
utopia-cms, 2018-2022, Aníbal Pacheco

Global variables definition, to avoid its definition multiple times inside the apps modules.
"""
import csv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from django.conf import settings


# mongodb database
try:
    client = MongoClient(serverSelectionTimeoutMS=1000)
    client.server_info()
    global mongo_db
    mongo_db = client[settings.MONGODB_DATABASE] if settings.MONGODB_DATABASE else None
except ServerSelectionTimeoutError:
    mongo_db = None

# blacklisted emails
global blacklisted
blacklisted = set(
    [row[0] for row in csv.reader(open(settings.CORE_NEWSLETTER_BLACKLIST))]
) if hasattr(settings, 'CORE_NEWSLETTER_BLACKLIST') else set()
