# coding=utf-8
import csv
import glob
import os
from tqdm import tqdm
from os.path import join

from django.conf import settings
from signupwall.middleware import get_article_by_url_path
from core.models import Article

filenames = [os.path.basename(x) for x in glob.glob(join(settings.DASHBOARD_REPORTS_PATH, "*audio_statistics.csv"))]

print("Starting changing/populating extra columns + renaming process...")
for filename in tqdm(filenames):
    with open(
        join(settings.DASHBOARD_REPORTS_PATH, filename)
    ) as csv_read, open(join(settings.DASHBOARD_REPORTS_PATH, filename + ".tmp"), "w") as csv_write:
        csvreader = csv.reader(csv_read)
        csvwriter = csv.writer(csv_write)
        for row in csvreader:
            article_url = row[1]
            try:
                article_obj = get_article_by_url_path(article_url)
                audio_length = article_obj.get_audio_length()
            except (Article.DoesNotExist, FileNotFoundError):
                audio_length = "ERROR"
            csvwriter.writerow(row[:3] + [row[3].split()[0], audio_length] + row[4:])
        os.rename(
            join(settings.DASHBOARD_REPORTS_PATH, filename),
            join(settings.DASHBOARD_REPORTS_PATH, filename + ".old"),
        )
        os.rename(
            join(settings.DASHBOARD_REPORTS_PATH, filename + ".tmp"),
            join(settings.DASHBOARD_REPORTS_PATH, filename),
        )
print("Finished")
