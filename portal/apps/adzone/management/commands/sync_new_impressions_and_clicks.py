from __future__ import print_function
from __future__ import unicode_literals
from django.core.management.base import BaseCommand

from apps import mongo_db

from adzone.models import AdImpression, AdClick


class Command(BaseCommand):
    help = "Sync new impressions and clicks registered in mongodb."

    def handle(self, *args, **options):
        first = True
        for i in mongo_db.adzone_impressions.find():
            if first:
                print('INSERT INTO %s(ad_id,source_ip,impression_date) VALUES' % AdImpression._meta.db_table)
                print("(%d,'%s','%s')" % (i['ad'], i['source_ip'], i['impression_date']))
                first = False
            else:
                print(",(%d,'%s','%s')" % (i['ad'], i['source_ip'], i['impression_date']))
            mongo_db.adzone_impressions.delete_one({'_id': i['_id']})
        if not first:
            print(';')
        first = True
        for c in mongo_db.adzone_clicks.find():
            if first:
                print('INSERT INTO %s(ad_id,source_ip,click_date) VALUES' % AdClick._meta.db_table)
                print("(%d,'%s','%s')" % (c['ad'], c['source_ip'], c['click_date']))
                first = False
            else:
                print(",(%d,'%s','%s')" % (c['ad'], c['source_ip'], c['click_date']))
            mongo_db.adzone_clicks.delete_one({'_id': c['_id']})
        if not first:
            print(';')
