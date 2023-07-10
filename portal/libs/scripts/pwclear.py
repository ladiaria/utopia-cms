from apps import mongo_db

mongo_db.signupwall_visitor.delete_many({})
#Out[2]: <pymongo.results.DeleteResult at 0x7f3a426c75a0>

mongo_db.core_articleviewedby.delete_many({})
#Out[3]: <pymongo.results.DeleteResult at 0x7f3a42f40870>

