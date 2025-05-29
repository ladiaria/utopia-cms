from django.core.management.base import BaseCommand

from apps import mongo_db

from adzone.models import AdImpression, AdClick, AdBase


class Command(BaseCommand):
    help = "Deletes new impressions and clicks registered in mongodb and prints the SQL to insert them in the RDB"

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep',
            action='store_true',
            default=False,
            dest='keep',
            help='Do not delete the impressions and clicks in mongodb',
        )

    def handle(self, *args, **options):
        keep, first, output = options.get('keep'), True, ""
        ad_ids, ad_ids_filtered = AdBase.objects.values_list('id', flat=True), set()
        for i in mongo_db.adzone_impressions.find():
            ad_id = i['ad']
            if ad_id in ad_ids_filtered or ad_id in ad_ids:
                ad_ids_filtered.add(ad_id)
                if first:
                    output += f'INSERT INTO {AdImpression._meta.db_table}(ad_id,source_ip,impression_date) VALUES\n'
                    first = False
                else:
                    output += "\n,"
                output += f"({ad_id},'{i['source_ip']}','{i['impression_date']}')"
                if not keep:
                    mongo_db.adzone_impressions.delete_one({'_id': i['_id']})
        if not first:
            output += ';\n'
        first = True
        for c in mongo_db.adzone_clicks.find():
            ad_id = c['ad']
            if ad_id in ad_ids_filtered or ad_id in ad_ids:
                ad_ids_filtered.add(ad_id)
                if first:
                    output += f'INSERT INTO {AdClick._meta.db_table}(ad_id,source_ip,click_date) VALUES\n'
                    first = False
                else:
                    output += "\n,"
                output += f"({ad_id},'{c['source_ip']}','{c['click_date']}')"
            if not keep:
                mongo_db.adzone_clicks.delete_one({'_id': c['_id']})
        if not first:
            output += ';'
        print(output)
