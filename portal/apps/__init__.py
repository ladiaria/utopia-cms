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
import requests
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from requests.auth import HTTPBasicAuth

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
global blocklisted, bouncer_blocklisted, document_type_choices
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


def crm_rest_api_kwargs(api_key, data=None):
    """
    Get the CRM API standard args.
    @param api_key: CRM API key.
    @param data: request body data to be send.
    @return result: dictionary with all params.
    """
    # we require the api_key as arg (we can obtain it from settings) because the caller code needs also it most of the
    # time to make previous conditions to call us or build the data arg, this way the code is a bit less repeated but
    # of course that the calls in all the code that call us can be refactored lettng this function with only one arg.
    http_basic_auth = settings.CRM_API_HTTP_BASIC_AUTH
    result = {"headers": {"X-Api-Key": api_key} if http_basic_auth else {'Authorization': 'Api-Key ' + api_key}}
    if not getattr(settings, "CRM_API_VERIFY_SSL", True):
        result["verify"] = False
    if data:
        result["data"] = data
    if http_basic_auth:
        result["auth"] = HTTPBasicAuth(*http_basic_auth)
    return result


def get_document_type_choices():
    if settings.DEBUG:
        print("get_document_type_choices called")
    result = []
    dtlist_json = getattr(settings, "THEDAILY_DOCUMENT_TYPE_CHOICES_JSON", None)
    if dtlist_json:
        api_base_url = settings.CRM_API_BASE_URI
        api_key = getattr(settings, 'CRM_UPDATE_USER_API_KEY', None)
        if api_base_url and api_key:
            # update, save and return the result
            try:
                # get from crm api
                response = requests.get(api_base_url + "document-types/", **crm_rest_api_kwargs(api_key))
                response.raise_for_status()
            except Exception as e:
                if settings.DEBUG:
                    print(e)
            else:
                # update local file
                try:
                    result = [(x["id"], x["name"]) for x in response.json()]
                    with open(dtlist_json, "w") as fobj:
                        json.dump(result, fobj)
                except Exception as e:
                    if settings.DEBUG:
                        print(e)
                else:
                    # return the result used to update the local file
                    return result
        # return content of the local file
        try:
            fobj = open(dtlist_json)
            result = json.loads(fobj.read())
            fobj.close()
        except FileNotFoundError as fnfe:
            if settings.DEBUG:
                print(fnfe)
    return result


document_type_choices = get_document_type_choices()
