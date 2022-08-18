# coding=utf-8
import csv
import glob
import os
from tqdm import tqdm
from os.path import join

from django.conf import settings
from signupwall.middleware import get_article_by_url_path
from core.models import Article

filenames = [os.path.basename(x) for x in glob.glob(join(settings.DASHBOARD_REPORTS_PATH, "*articles.csv"))]

print("Starting populating extra columns + renaming process...")
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
                if article_obj.main_section.section and article_obj.main_section.section.category:
                    category_or_publication = article_obj.main_section.section.category
                else:
                    category_or_publication = article_obj.main_section.edition.publication
                if article_obj.publication_section():
                    section = article_obj.publication_section().name
                else:
                    section = None
            except (Article.DoesNotExist, AttributeError):
                category_or_publication = ""
                section = ""
            csvwriter.writerow([
                row[0],  # i
                row[1],  # url
                row[2],  # views
                row[3],  # published_in
                section,
                category_or_publication,
                row[4],  # score
            ])
        os.rename(
            join(settings.DASHBOARD_REPORTS_PATH, filename),
            join(settings.DASHBOARD_REPORTS_PATH, filename + ".old"),
        )

        os.rename(
            join(settings.DASHBOARD_REPORTS_PATH, filename + ".tmp"),
            join(settings.DASHBOARD_REPORTS_PATH, filename),
        )
print("Finished")
