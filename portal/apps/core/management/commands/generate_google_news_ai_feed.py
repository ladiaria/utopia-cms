import os
from datetime import date, timedelta

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.test import RequestFactory

from core.models import Article
from feeds import GoogleNewsAIFeedByDate


class Command(BaseCommand):
    help = "Generate Google News AI RSS XML files (one per day) for bulk quarterly transfer to Google Drive."

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=date.fromisoformat,
            required=True,
            help='First day to generate (YYYY-MM-DD, inclusive).',
        )
        parser.add_argument(
            '--end-date',
            type=date.fromisoformat,
            required=True,
            help='Last day to generate (YYYY-MM-DD, inclusive).',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='/tmp/google-news-ai-feed',
            help='Directory where XML files will be saved (default: /tmp/google-news-ai-feed).',
        )

    def handle(self, *args, **options):
        start_date = options['start_date']
        end_date = options['end_date']
        output_dir = options['output_dir']

        if start_date > end_date:
            raise CommandError('--start-date must be before or equal to --end-date.')

        os.makedirs(output_dir, exist_ok=True)

        # Build a fake request so Django's Feed framework can construct absolute URLs.
        port = '443' if settings.URL_SCHEME == 'https' else '80'
        request = RequestFactory().get(
            '/',
            SERVER_NAME=settings.SITE_DOMAIN,
            SERVER_PORT=port,
            secure=(settings.URL_SCHEME == 'https'),
        )

        current = start_date
        generated = 0
        skipped = 0

        while current <= end_date:
            articles = Article.published.filter(
                date_published__date=current,
            ).order_by('date_published')

            if not articles.exists():
                self.stdout.write(f'  {current} — no articles, skipping')
                skipped += 1
                current += timedelta(days=1)
                continue

            feed_view = GoogleNewsAIFeedByDate(articles, include_images=False)
            feed_obj = feed_view.get_feed(None, request)

            filename = f'feed-{current}.xml'
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'wb') as f:
                feed_obj.write(f, 'utf-8')

            self.stdout.write(f'  {current} — {articles.count()} articles → {filename}')
            generated += 1
            current += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {generated} files generated, {skipped} days skipped (no articles). Output: {output_dir}'
        ))
