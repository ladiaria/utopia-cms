# coding:utf-8
from time import sleep

from django.test import TransactionTestCase, tag

from core.models import Publication, Article


@tag('celery')
class CelerytasksTestCase(TransactionTestCase):

    fixtures = ['test']

    def test01_pub_slug_change_updates_articles_urls(self):
        p = Publication.objects.get(slug="spinoff")
        first_article = Article.objects.filter(main_section__edition__publication=p)[0]
        self.assertTrue(first_article.url_path.startswith("/spinoff/"))
        p.slug = "spinoffpub"
        p.save()
        sleep(5)  # give time to celery execute the task
        first_article = Article.objects.filter(main_section__edition__publication=p)[0]
        self.assertTrue(first_article.url_path.startswith("/spinoffpub/"))
        p.slug = "spinoff"
        p.save()
        sleep(5)  # give time to celery execute the task
        self.assertTrue(
            Article.objects.filter(main_section__edition__publication=p)[0].url_path.startswith("/spinoff/")
        )
