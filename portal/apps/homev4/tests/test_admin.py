"""
Unit tests for homev4/admin.py — admin locking integration.

Tests cover:
 - HomeLayoutAdmin.Media has the correct JS files for django-admin-locking.
 - HomeLayout is registered in the Django admin site.
 - AdminLockingBase is wired into HomeLayoutAdmin's MRO.
 - Conditional import: empty mixin when ADMIN_PAGE_LOCK_ENABLED=False.
 - Conditional import: AdminLockingMixin used when ADMIN_PAGE_LOCK_ENABLED=True.
 - ImportError fallback: empty mixin when library is missing but setting is True.

Note: settings.py does `from local_settings import *`, so even in test mode
ADMIN_PAGE_LOCK_ENABLED can be True. Tests that need a specific value use
@override_settings and importlib.reload() to re-evaluate the conditional import.
"""
import importlib
import sys
from unittest import mock

from django.contrib import admin as django_admin
from django.test import SimpleTestCase, override_settings

from homev4.models import HomeLayout, HomeLayoutAuditLog


class HomeLayoutAdminMediaTest(SimpleTestCase):

    def test_media_includes_admin_locking_js(self):
        from homev4.admin import HomeLayoutAdmin
        self.assertIn('admin_locking/admin_locking.js', HomeLayoutAdmin.Media.js)

    def test_media_includes_custom_js(self):
        from homev4.admin import HomeLayoutAdmin
        self.assertIn('js/admin_locking_custom.js', HomeLayoutAdmin.Media.js)


class HomeLayoutAdminRegistrationTest(SimpleTestCase):

    def test_homelayout_is_registered(self):
        self.assertIn(HomeLayout, django_admin.site._registry)

    def test_registered_admin_class(self):
        # Fresh import so we get the current class even after reloads in other tests.
        from homev4.admin import HomeLayoutAdmin
        self.assertIsInstance(django_admin.site._registry[HomeLayout], HomeLayoutAdmin)


class HomeLayoutAdminStructureTest(SimpleTestCase):

    def test_admin_locking_base_in_mro(self):
        from homev4.admin import AdminLockingBase, HomeLayoutAdmin
        self.assertIn(AdminLockingBase, HomeLayoutAdmin.__mro__)

    def test_admin_locking_base_precedes_model_admin(self):
        # AdminLockingBase must appear before ModelAdmin so its hooks take priority.
        from homev4.admin import AdminLockingBase, HomeLayoutAdmin
        mro = list(HomeLayoutAdmin.__mro__)
        self.assertLess(mro.index(AdminLockingBase), mro.index(django_admin.ModelAdmin))


class AdminLockingBaseConditionalImportTest(SimpleTestCase):
    """
    Test the conditional import logic in homev4/admin.py by reloading the module
    with controlled settings and sys.modules state.
    """

    def _reload_admin(self):
        """Reload homev4.admin; unregister models first to avoid AlreadyRegistered."""
        import homev4.admin as mod
        # @admin.register() re-runs on reload, so unregister first.
        for model in (HomeLayout, HomeLayoutAuditLog):
            try:
                django_admin.site.unregister(model)
            except django_admin.sites.NotRegistered:
                pass
        importlib.reload(mod)
        return mod

    def tearDown(self):
        # Restore the module to its real state (using current local_settings).
        self._reload_admin()

    @override_settings(ADMIN_PAGE_LOCK_ENABLED=False)
    def test_empty_mixin_when_disabled(self):
        mod = self._reload_admin()
        public_methods = {m for m in dir(mod.AdminLockingBase) if not m.startswith('_')}
        self.assertEqual(public_methods, set())

    @override_settings(ADMIN_PAGE_LOCK_ENABLED=True)
    def test_uses_mixin_when_enabled_and_library_present(self):
        mock_mixin = type('AdminLockingMixin', (), {'locking_marker': True})
        mock_locking_admin = mock.MagicMock()
        mock_locking_admin.AdminLockingMixin = mock_mixin

        with mock.patch.dict(sys.modules, {
            'admin_locking': mock.MagicMock(),
            'admin_locking.admin': mock_locking_admin,
        }):
            mod = self._reload_admin()

        self.assertIs(mod.AdminLockingBase, mock_mixin)

    @override_settings(ADMIN_PAGE_LOCK_ENABLED=True)
    def test_empty_fallback_when_library_missing(self):
        # Setting a key to None in sys.modules makes Python raise ImportError on import.
        with mock.patch.dict(sys.modules, {'admin_locking': None, 'admin_locking.admin': None}):
            mod = self._reload_admin()

        public_methods = {m for m in dir(mod.AdminLockingBase) if not m.startswith('_')}
        self.assertEqual(public_methods, set())
