# coding=utf-8
from __future__ import division

import csv
import glob
import os
from tqdm import tqdm
from os.path import join
from datetime import datetime, date, timedelta
from dateutil import relativedelta

from django.conf import settings
from signupwall.middleware import get_article_by_url_path
from core.models import Publication, ArticleRel


filenames = [os.path.basename(x) for x in glob.glob(join(settings.DASHBOARD_REPORTS_PATH, "*categories.csv"))]
filenames.sort()

print("Fixing publications article counters + renaming process...")
for filename in tqdm(filenames):
    with open(
        join(settings.DASHBOARD_REPORTS_PATH, filename)
    ) as csv_read, open(join(settings.DASHBOARD_REPORTS_PATH, filename + ".tmp"), "w") as csv_write:
        csvreader = csv.reader(csv_read)
        csvwriter = csv.writer(csv_write)
        filename_parts = filename.split("_")
        if len(filename_parts) > 1:
            ds_month_first = datetime.strptime(filename_parts[0] + "01", "%Y%m%d").date()
        else:
            this_month_first = date.today().replace(day=1)
            last_month = this_month_first - timedelta(1)
            ds_month_first = datetime.combine(last_month.replace(day=1), datetime.min.time()).date()
        dt_until = ds_month_first + relativedelta.relativedelta(months=1)
        for row in csvreader:
            try:
                pub_obj = Publication.objects.get(name=row[1])
            except Publication.DoesNotExist:
                pass
            else:
                row[2] = len(
                    set(
                        [
                            ar.article.id for ar in ArticleRel.objects.filter(
                                edition__publication=pub_obj,
                                article__date_published__gte=ds_month_first,
                                article__date_published__lt=dt_until,
                                article__is_published=True,
                            )
                        ]
                    )
                )
                row[4] = (int(row[3]) / row[2]) if row[2] else 0  # upd also score per article
            csvwriter.writerow(row)
        os.rename(
            join(settings.DASHBOARD_REPORTS_PATH, filename),
            join(settings.DASHBOARD_REPORTS_PATH, filename + ".old"),
        )
        os.rename(
            join(settings.DASHBOARD_REPORTS_PATH, filename + ".tmp"),
            join(settings.DASHBOARD_REPORTS_PATH, filename),
        )
print("Finished")
