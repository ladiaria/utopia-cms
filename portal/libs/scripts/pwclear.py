from apps import mongo_db


def pwclear():
    if mongo_db is not None:
        mongo_db.signupwall_visitor.delete_many({})
        # Out[2]: <pymongo.results.DeleteResult at 0x7f3a426c75a0>

        mongo_db.core_articleviewedby.delete_many({})
        # Out[3]: <pymongo.results.DeleteResult at 0x7f3a42f40870>


def phone_subscription_log_clear():
    if mongo_db is not None:
        mongo_db.phone_subscription_log.delete_many({})
