# coding:utf-8
from actstream.models import Follow

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from core.factories import UserFactory
from core.models import Article, Section
from . import PreCopyImage


class SectionTestCase(PreCopyImage):

    fixtures = ['test']

    def test01_latest(self):
        s1 = Section.objects.get(id=1)
        # 1 - without params
        # article9 should be the first because is the one with the latest date_published
        self.assertEqual(s1.latest()[0].id, 9)

    def test02_section_back_publication(self):
        with self.settings(CORE_SECTION_MAIN_PUBLICATION={'spinoff': ['news']}):
            s1 = Section.objects.get(id=1)
            c = Client()
            res = c.get('/seccion/{}/'.format(s1.slug), {}, HTTP_HOST=settings.SITE_DOMAIN)
            self.assertEqual(res.status_code, 200)
            # test the go back link href with the publication slug is present in the view
            self.assertRegex(res.content.decode(), r'<a class=".*" href="/spinoff/">')

    def test03_section_detail_marks_followed_articles_as_saved(self):
        """A followed (read-later) article must render its bookmark in the "added" state.

        section_detail() must populate context['follows'] with a single query so the card template
        (which passes prefetched_article_data=True) checks `a.id in follows` instead of leaving every
        bookmark in the default unsaved state. See PERFORMANCE.md.
        """
        section = Section.objects.get(id=1)
        followed = section.latest()[0]
        not_followed = next(a for a in section.latest() if a.id != followed.id)

        user = UserFactory()
        Follow.objects.create(
            user=user,
            content_type=ContentType.objects.get_for_model(Article),
            object_id=str(followed.id),
        )

        c = Client()
        c.force_login(user)
        res = c.get('/seccion/{}/'.format(section.slug), {}, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(res.status_code, 200)

        content = res.content.decode()
        # The followed article shows the "added" bookmark; a non-followed one does not.
        self.assertIn('added" title="Quitar de leer después" data-article-id="%d"' % followed.id, content)
        self.assertNotIn(
            'added" title="Quitar de leer después" data-article-id="%d"' % not_followed.id, content
        )

    def test04_section_detail_batches_author_queries(self):
        """Authors must be prefetched so get_authors() does not issue one query per article (N+1).

        The card template calls article.get_authors() (article.byline.all()) for every article on the
        page; without prefetch_related('byline') that is one core_journalist query per article.
        """
        section = Section.objects.get(id=1)
        c = Client()
        with CaptureQueriesContext(connection) as ctx:
            res = c.get('/seccion/{}/'.format(section.slug), {}, HTTP_HOST=settings.SITE_DOMAIN)
        self.assertEqual(res.status_code, 200)

        author_queries = [q for q in ctx.captured_queries if 'core_article_byline' in q['sql']]
        # A single batched prefetch, not one query per article on the page.
        self.assertLessEqual(
            len(author_queries), 1,
            "Expected authors to be prefetched in one query, got %d: %s" % (
                len(author_queries), [q['sql'] for q in author_queries]
            ),
        )
