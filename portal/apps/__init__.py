# coding:utf8
"""
utopia-cms, 2018-2021, Aníbal Pacheco

Global variables definition, to avoid its definition multiple times inside the apps modules.
"""
import csv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from django.conf import settings


# mongodb tables
try:
    client = MongoClient(serverSelectionTimeoutMS=1000)
    client.server_info()
    global core_articleviewedby_mdb, core_articlevisits_mdb, signupwall_visitor_mdb, adzone_mdb
    core_articleviewedby_mdb, core_articlevisits_mdb, signupwall_visitor_mdb, adzone_mdb = (
        client[settings.CORE_MONGODB_ARTICLEVIEWEDBY] if settings.CORE_MONGODB_ARTICLEVIEWEDBY else None,
        client[settings.CORE_MONGODB_ARTICLEVISITS] if settings.CORE_MONGODB_ARTICLEVISITS else None,
        client[settings.SIGNUPWALL_MONGODB_VISITOR] if settings.SIGNUPWALL_MONGODB_VISITOR else None,
        client[settings.ADZONE_MONGODB] if settings.ADZONE_MONGODB else None,
    )
except ServerSelectionTimeoutError:
    core_articleviewedby_mdb = core_articlevisits_mdb = signupwall_visitor_mdb = adzone_mdb = None

# blacklisted emails
global blacklisted
blacklisted = set(
    [row[0] for row in csv.reader(open(settings.CORE_NEWSLETTER_BLACKLIST))]
) if hasattr(settings, 'CORE_NEWSLETTER_BLACKLIST') else set()
