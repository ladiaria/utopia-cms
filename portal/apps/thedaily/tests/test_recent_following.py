# coding:utf-8
"""
Regression tests for recent_following() and the lista-lectura views that consume it.

Background: actstream stores follows with a GenericForeignKey. When the followed object is
deleted, follow.follow_object resolves to None. recent_following() used to return those Nones
verbatim; the 2026-05-28 select_related refactor of lista_lectura_leer_despues() then did
[a.id for a in ...], raising "'NoneType' object has no attribute 'id'". See PERFORMANCE.md.
"""
from actstream.models import Follow

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from core.models import Article
from core.factories import UserFactory
from thedaily.utils import recent_following


class RecentFollowingDeletedObjectTest(TestCase):
    def _make_orphan_follow(self, user, offset=0):
        """Create a Follow row pointing at an Article id that does not exist.

        This is exactly the state left behind when a followed article is deleted: the Follow
        survives but its generic FK no longer resolves to an object.
        """
        article_ct = ContentType.objects.get_for_model(Article)
        max_id = Article.objects.order_by('-id').values_list('id', flat=True).first() or 0
        missing_id = max_id + 1000 + offset
        return Follow.objects.create(user=user, content_type=article_ct, object_id=str(missing_id))

    def test_recent_following_skips_deleted_objects(self):
        user = UserFactory()
        self._make_orphan_follow(user)
        # Must not contain None, even though the followed article no longer exists.
        result = recent_following(user, Article)
        self.assertNotIn(None, result)
        self.assertEqual(result, [])

    def test_recent_following_count_excludes_deleted(self):
        """The count shown in the UI ('Leer después (N)') must not include orphaned follows."""
        user = UserFactory()
        self._make_orphan_follow(user, offset=0)
        self._make_orphan_follow(user, offset=1)
        self.assertEqual(len(recent_following(user, Article)), 0)
