# -*- coding: utf-8 -*-
from django.utils.timezone import now
from django.core.management.base import BaseCommand

from core.models import Article


class Command(BaseCommand):
    help = 'Publish the articles based on the date_publishing'

    def handle(self, *args, **options):
        articles_to_publish = Article.objects.filter(date_published__lte=now())
        for article in articles_to_publish:
            article.is_published = True
            article.save()  # this handle the publishing date
