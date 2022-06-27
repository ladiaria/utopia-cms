from django.conf import settings


print("""
# execute this commands in mongo shell:
> use {ADZONE_MONGODB};
> db.impressions.renameCollection('adzone_impressions');
> db.clicks.renameCollection('adzone_clicks');
> exit;

# execute this commands to build only one mongo db with all data:
mongodump -d {ADZONE_MONGODB} -o mongodump/
mongorestore -d {MONGODB_DATABASE} mongodump/{ADZONE_MONGODB}

mongodump -d {CORE_MONGODB_ARTICLEVIEWEDBY} -c posts
mongodump -d {CORE_MONGODB_ARTICLEVISITS} -c posts
mongodump -d {SIGNUPWALL_MONGODB_VISITOR} -c posts

mongorestore -d {MONGODB_DATABASE} -c core_articleviewedby dump/{CORE_MONGODB_ARTICLEVIEWEDBY}/posts.bson
mongorestore -d {MONGODB_DATABASE} -c core_articlevisits dump/{CORE_MONGODB_ARTICLEVISITS}/posts.bson
mongorestore -d {MONGODB_DATABASE} -c signupwall_visitor dump/{SIGNUPWALL_MONGODB_VISITOR}/posts.bson

# remove dumps and old databases:
rm -rf mongodump dump

# execute this commands in mongo shell:
> use {ADZONE_MONGODB};
> db.dropDatabase();
> use {CORE_MONGODB_ARTICLEVIEWEDBY};
> db.dropDatabase();
> use {CORE_MONGODB_ARTICLEVISITS};
> db.dropDatabase();
> use {SIGNUPWALL_MONGODB_VISITOR};
> db.dropDatabase();
> exit;
""".format(
    ADZONE_MONGODB=getattr(settings, 'ADZONE_MONGODB', 'ldsocial_adzone'),
    MONGODB_DATABASE=settings.MONGODB_DATABASE,
    CORE_MONGODB_ARTICLEVIEWEDBY=getattr(settings, 'CORE_MONGODB_ARTICLEVIEWEDBY', 'ldsocial_core_articleviewedby'),
    CORE_MONGODB_ARTICLEVISITS=getattr(settings, 'CORE_MONGODB_ARTICLEVISITS', 'ldsocial_core_articlevisits'),
    SIGNUPWALL_MONGODB_VISITOR=getattr(settings, 'SIGNUPWALL_MONGODB_VISITOR', 'ldsocial_signupwall_visitor'),
))
