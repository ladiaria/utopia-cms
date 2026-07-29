# coding:utf-8
"""
Tests for find_user_by_contact_email, the lookup shared by both CRM->CMS sync channels
(the update_subscribers command and the sync API view in thedaily.views).

Background: the sync used to look the account up by User.email only, while the CMS validates a
new email against three places (User.email, User.username and UserSocialAuth.uid). Looking up
narrower than it validates made the sync conclude "this contact has no account", try to create
one, and get rejected by the validation. The person had paid and stayed without access, and the
run failed again every night because nothing changed.

Each test below is one of the shapes actually found in production on 2026-07-29.
"""
from social_django.models import UserSocialAuth

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from thedaily.utils import find_user_by_contact_email


# MX validation would hit real DNS for every user created here, and the CRM push on save is not
# what these tests are about.
@override_settings(THEDAILY_VALIDATE_EMAIL_CHECK_MX=False, CRM_UPDATE_USER_ENABLED=False)
class FindUserByContactEmailTestCase(TestCase):

    def test_found_by_email(self):
        """The case that already worked before the fix: it must keep working."""
        user = User.objects.create_user("someone@example.com", "someone@example.com")

        found, matched_by = find_user_by_contact_email("someone@example.com")

        self.assertEqual(found, user)
        self.assertEqual(matched_by, "email")

    def test_found_by_username_when_account_email_is_blank(self):
        """
        Production contact 701050: the account carries the address in `username` and its `email`
        field is empty, so the old lookup missed it and tried to create a duplicate account.
        """
        # create_user(username, email): same address as username, empty email field
        user = User.objects.create_user("lyaques@example.com", "")

        found, matched_by = find_user_by_contact_email("lyaques@example.com")

        self.assertEqual(found, user)
        self.assertEqual(matched_by, "username")

    def test_found_by_username_when_account_has_another_email(self):
        """
        Same lookup, but the account already has a different address in `email`. Still the same
        person (`username` is unique and is the exact CRM address), so it must be linked. What
        the caller does with the differing email is update_email()'s call, not this function's.
        """
        user = User.objects.create_user("olduser@example.com", "another@example.com")

        found, matched_by = find_user_by_contact_email("olduser@example.com")

        self.assertEqual(found, user)
        self.assertEqual(matched_by, "username")

    def test_google_login_of_another_account_is_not_linked(self):
        """
        Production contacts 708642 and 726884, and the reason this function exists.

        The address is registered as a Google login (UserSocialAuth.uid) of an account that is
        registered under a *different* address and already belongs to somebody else. Linking it
        would hand the subscription the contact paid for to the wrong person, so the function
        must refuse and let a human decide.

        Note this branch is only reached when no account carries the address in email or
        username, which is exactly when the association cannot be attributed automatically.
        """
        somebody_else = User.objects.create_user("ana@example.com", "ana@example.com")
        UserSocialAuth.objects.create(
            user=somebody_else, provider="google-oauth2", uid="carlos@example.com"
        )

        found, matched_by = find_user_by_contact_email("carlos@example.com")

        self.assertIsNone(found)
        self.assertEqual(matched_by, "social_auth_conflict")

    def test_unknown_email_is_safe_to_create(self):
        """No account anywhere: the caller should go ahead and create one."""
        found, matched_by = find_user_by_contact_email("nobody@example.com")

        self.assertIsNone(found)
        self.assertIsNone(matched_by)

    def test_blank_email(self):
        """Contacts with no email in the CRM reach the sync too, and must not match anything."""
        # an account with an empty email field must not be matched by an empty lookup
        User.objects.create_user("someuser@example.com", "")

        self.assertEqual(find_user_by_contact_email(""), (None, None))
        self.assertEqual(find_user_by_contact_email(None), (None, None))
