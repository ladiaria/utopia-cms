from apps import mongo_db


def pwclear(visitors_only=False, ip=None):
    if mongo_db is not None:
        mongo_db.signupwall_visitor.delete_many({"ip": ip} if ip else {})
        if not visitors_only:
            mongo_db.core_articleviewedby.delete_many({})


def phone_subscription_log_clear():
    if mongo_db is not None:
        mongo_db.phone_subscription_log.delete_many({})
