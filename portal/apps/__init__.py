from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from django.conf import settings


try:
    client = MongoClient(serverSelectionTimeoutMS=1000)
    client.server_info()
    global core_articleviewedby_mdb, core_articlevisits_mdb, signupwall_visitor_mdb
    core_articleviewedby_mdb, core_articlevisits_mdb, signupwall_visitor_mdb = (
        client[settings.CORE_MONGODB_ARTICLEVIEWEDBY] if settings.CORE_MONGODB_ARTICLEVIEWEDBY else None,
        client[settings.CORE_MONGODB_ARTICLEVISITS] if settings.CORE_MONGODB_ARTICLEVISITS else None,
        client[settings.SIGNUPWALL_MONGODB_VISITOR] if settings.SIGNUPWALL_MONGODB_VISITOR else None)
except ServerSelectionTimeoutError:
    core_articleviewedby_mdb = core_articlevisits_mdb = signupwall_visitor_mdb = None
