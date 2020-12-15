# -*- coding: utf-8 -*-
# la diaria 2020. Aníbal Pacheco.

"""
1. set SIGNUPWALL_MONGODB_VISITOR to None in local_settings before running this script in a "live" environment.
2. touch uwsgi.ini.
3. run this script.
4. drop old table:

mongo
> use ldsocial_signupwall_visitor
> db.dropDatabase()

5. rename new table with the old table name and add indexes:

mongodump --archive="visitor_new" --db=ldsocial_signupwall_visitor_new
mongorestore --archive="visitor_new" --nsFrom='ldsocial_signupwall_visitor_new.*' --nsTo='ldsocial_signupwall_visitor.*'
mongo
> use ldsocial_signupwall_visitor_new
> db.dropDatabase()
> use ldsocial_signupwall_visitor
> db.posts.createIndex({'timestamp': -1})
> db.posts.createIndex({'session_key': -1})
> db.posts.createIndex({'ip_address': -1})
> db.posts.createIndex({'user': -1})

6. return the local setting to its original value.
7. deploy branch with the modifications to use the new table.
"""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from progress.bar import Bar

try:
    client = MongoClient(serverSelectionTimeoutMS=1000)
    client.server_info()
    signupwall_visitor_mdb = client['ldsocial_signupwall_visitor']
    signupwall_visitor_mdb_new = client['ldsocial_signupwall_visitor_new']
except ServerSelectionTimeoutError:
    signupwall_visitor_mdb = signupwall_visitor_mdb_new = None


if signupwall_visitor_mdb and signupwall_visitor_mdb_new:
    visitors = signupwall_visitor_mdb.posts.find({'paths_visited': {'$exists': True}}, no_cursor_timeout=True)
    bar = Bar('Processing ...', max=visitors.count())
    for v in visitors:
        paths_visited = v.get('paths_visited')
        if paths_visited:
            migrated = {'timestamp': v['last_update'], 'session_key': v['session_key'], 'ip_address': v['ip_address']}
            user = v.get('user')
            if user:
                migrated.update({'user': user})
            signupwall_visitor_mdb_new.posts.insert_many([dict(migrated, path_visited=p) for p in paths_visited])
        bar.next()
    bar.finish()
