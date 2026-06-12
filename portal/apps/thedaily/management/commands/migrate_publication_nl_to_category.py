# -*- coding: utf-8 -*-
"""
Migrate newsletter subscribers from a publication newsletter to a category (area) newsletter,
or the other way around with --reverse (rollback).

Built for the deporte/Mundial migration (trello4124) but generic: publication and category are
given by slug. Default mode is DRY-RUN: nothing is written unless --execute is passed.

Design notes (why this command does what it does):

* The m2m_changed signal (thedaily.models.subscriber_newsletters_changed) already syncs the CRM,
  but it swallows CRM errors silently (except RequestException: pass), which makes a bulk
  migration unauditable. So this command suppresses the signal per-subscriber (setting the
  in-memory "updatefromcrm" attribute, the same flag the signal checks to avoid CRM->CMS loops)
  and performs the same updatecrmuser() calls itself, with explicit error handling, retry and a
  failures file.

* Per-subscriber operation order guarantees safe resumability: the subscriber is removed from
  the SOURCE newsletter in the CMS only as the LAST step, after both CRM calls succeeded.
  Membership in the source newsletter is therefore the "not migrated yet" marker, and re-running
  the command retries exactly the pending/failed ones. All steps are idempotent on both sides
  (M2M add/remove in the CMS; get_or_create / filter().delete() in the CRM).

* Subscribers without contact_id exist only in the CMS, so they are migrated with CMS operations
  only. This is why the final CMS/CRM counts are not expected to be 1:1.
"""

import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import Category, Publication
from thedaily.models import Subscriber, updatecrmuser


class Command(BaseCommand):
    help = (
        "Migrate subscribers from a publication newsletter to a category newsletter (or back with "
        "--reverse). Dry-run by default; use --execute to apply changes."
    )

    def add_arguments(self, parser):
        parser.add_argument("publication_slug", type=str, help="Publication slug (e.g. 'deporte')")
        parser.add_argument("category_slug", type=str, help="Category slug (e.g. 'deporte')")
        parser.add_argument(
            "--reverse",
            action="store_true",
            help="Rollback direction: migrate category newsletter subscribers back to the publication newsletter",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Apply the changes. Without this flag the command only reports what it would do (dry-run)",
        )
        parser.add_argument(
            "--ids", nargs="+", type=int, metavar="SUBSCRIBER_ID", help="Limit to these subscriber ids (canary runs)"
        )
        parser.add_argument(
            "--emails", nargs="+", type=str, metavar="EMAIL", help="Limit to subscribers with these emails (canary runs)"
        )
        parser.add_argument("--limit", type=int, help="Process at most this many subscribers")
        parser.add_argument(
            "--cms-only",
            action="store_true",
            help=(
                "Skip CRM calls entirely (CMS-side move only). Required explicitly when CRM sync is disabled, "
                "to prevent migrating the CMS while silently leaving the CRM untouched"
            ),
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0,
            metavar="SECONDS",
            help="Pause between subscribers to throttle CRM calls (default: 0)",
        )
        parser.add_argument(
            "--failures-file",
            type=str,
            help="Path of the JSONL file where failures are appended (default: ./migrate_nl_failures_<ts>.jsonl)",
        )
        parser.add_argument(
            "--progress-every", type=int, default=100, metavar="N", help="Print progress every N subscribers"
        )

    def crm_call(self, contact_id, field, value):
        """
        Call updatecrmuser with one retry. Returns (ok, error_message).
        A None response with CRM enabled means a misconfiguration in put_data_to_crm (missing URL
        or API key, which make it return None silently) — treated as failure to keep the audit honest.
        """
        last_error = None
        for attempt in (1, 2):
            try:
                response = updatecrmuser(contact_id, field, json.dumps(value))
                if response is None:
                    return False, "updatecrmuser returned None (CRM sync disabled or missing URL/API key)"
                # The CRM contact_api returns HTTP 200 with {"contact_id": null} when the contact does
                # not exist (it silently does nothing). Detect that signature so subscribers with stale
                # contact_ids land in the failures file instead of counting as migrated.
                if isinstance(response, dict) and response.get("contact_id") is None:
                    return False, "contact_id %s not found in CRM (response: %s)" % (contact_id, response)
                return True, None
            except Exception as exc:
                last_error = "%s: %s" % (type(exc).__name__, exc)
                # brief pause before the single retry, to survive transient network hiccups
                if attempt == 1:
                    time.sleep(0.5)
        return False, last_error

    def record_failure(self, failures_path, subscriber, phase, error):
        # JSONL append so a crashed run still leaves a usable audit trail of everything before the crash
        with open(failures_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "ts": timezone.now().isoformat(),
                        "subscriber_id": subscriber.id,
                        "email": getattr(subscriber.user, "email", None) if subscriber.user_id else None,
                        "contact_id": subscriber.contact_id,
                        "phase": phase,
                        "error": error,
                    }
                )
                + "\n"
            )

    def handle(self, *args, **options):
        try:
            publication = Publication.objects.get(slug=options["publication_slug"])
        except Publication.DoesNotExist:
            raise CommandError("Publication with slug '%s' not found" % options["publication_slug"])
        try:
            category = Category.objects.get(slug=options["category_slug"])
        except Category.DoesNotExist:
            raise CommandError("Category with slug '%s' not found" % options["category_slug"])

        reverse, execute, cms_only = options["reverse"], options["execute"], options["cms_only"]

        # Direction setup. The CRM field names mirror exactly what the m2m_changed signal would
        # send: 'newsletters' / 'area_newsletters' for adds, plus '_remove' suffix for removals,
        # so the CRM-side update_customer() processing is identical to the organic flow.
        if reverse:
            source_label = "category '%s' (id %d)" % (category.slug, category.id)
            target_label = "publication '%s' (id %d)" % (publication.slug, publication.id)
            crm_add_field, crm_add_value = "newsletters", [publication.id]
            crm_remove_field, crm_remove_value = "area_newsletters_remove", [category.id]
            base_qs = Subscriber.objects.filter(category_newsletters=category)
        else:
            source_label = "publication '%s' (id %d)" % (publication.slug, publication.id)
            target_label = "category '%s' (id %d)" % (category.slug, category.id)
            crm_add_field, crm_add_value = "area_newsletters", [category.id]
            crm_remove_field, crm_remove_value = "newsletters_remove", [publication.id]
            base_qs = Subscriber.objects.filter(newsletters=publication)

        qs = base_qs.select_related("user").order_by("id")
        if options["ids"]:
            qs = qs.filter(id__in=options["ids"])
        if options["emails"]:
            qs = qs.filter(user__email__in=options["emails"])
        if options["limit"]:
            qs = qs[: options["limit"]]

        total = qs.count()
        with_contact = qs.exclude(contact_id__isnull=True).count()
        without_contact = total - with_contact

        crm_enabled = bool(getattr(settings, "CRM_UPDATE_USER_ENABLED", False))
        self.stdout.write(self.style.MIGRATE_HEADING("Newsletter migration: %s -> %s" % (source_label, target_label)))
        self.stdout.write("Mode: %s" % ("EXECUTE" if execute else "DRY-RUN (no changes will be made)"))
        self.stdout.write("CRM sync enabled (CRM_UPDATE_USER_ENABLED): %s%s" % (crm_enabled, " [--cms-only]" if cms_only else ""))
        self.stdout.write("Universe: %d subscribers (%d with contact_id, %d CMS-only)" % (total, with_contact, without_contact))

        # Cutover-prerequisite warnings (do not block this command, but the web subscribe/unsubscribe
        # endpoints gate on has_newsletter, so flags must be flipped at cutover time).
        target_obj = publication if reverse else category
        if not target_obj.has_newsletter:
            self.stdout.write(self.style.WARNING(
                "WARNING: target %s has has_newsletter=False — users won't be able to manage this NL on the web "
                "until the flag is enabled" % target_label
            ))

        # Refuse to run a "half migration" by accident: with CRM sync disabled, CMS changes would
        # be applied while every CRM call silently does nothing.
        if execute and not cms_only and with_contact and not crm_enabled:
            raise CommandError(
                "%d subscribers have contact_id but CRM sync is disabled (CRM_UPDATE_USER_ENABLED=False). "
                "Enable it or pass --cms-only explicitly to migrate the CMS side only." % with_contact
            )

        if not execute:
            self.stdout.write("\nSample of subscribers that would be migrated (first 10):")
            for s in qs[:10]:
                self.stdout.write(
                    "  id=%d email=%s contact_id=%s" % (s.id, getattr(s.user, "email", "-"), s.contact_id or "-")
                )
            if total > 10:
                self.stdout.write("  ... and %d more" % (total - 10))
            self.stdout.write("\nPer subscriber with contact_id, the CRM would receive (in this order):")
            self.stdout.write("  1. PUT field=%s value=%s" % (crm_add_field, json.dumps(crm_add_value)))
            self.stdout.write("  2. PUT field=%s value=%s" % (crm_remove_field, json.dumps(crm_remove_value)))
            self.stdout.write(self.style.SUCCESS("\nDry-run finished. Re-run with --execute to apply."))
            return

        failures_path = options["failures_file"] or "migrate_nl_failures_%s.jsonl" % timezone.now().strftime("%Y%m%d-%H%M%S")
        migrated = cms_only_migrated = failed = processed = 0

        # list(values_list) of ids first: the queryset shrinks while we remove source memberships,
        # so iterating the queryset directly would skip rows (classic mutate-while-iterating bug).
        subscriber_ids = list(qs.values_list("id", flat=True))
        for sid in subscriber_ids:
            subscriber = Subscriber.objects.select_related("user").get(id=sid)
            processed += 1

            # Suppress the m2m_changed -> CRM sync signal: this command makes the CRM calls itself
            # so failures can be captured, retried and audited (the signal swallows them).
            subscriber.updatefromcrm = True

            # Step 1 (CMS add, idempotent): subscriber gets the target NL. Doing it first means a
            # failure later leaves them subscribed in both lists, never in none.
            if reverse:
                subscriber.newsletters.add(publication)
            else:
                subscriber.category_newsletters.add(category)

            if subscriber.contact_id and not cms_only:
                # Step 2 (CRM add): on failure keep the subscriber in the source NL (CMS) so the
                # re-run selects them again; receiving the NL twice is impossible because only one
                # send command will be active at any time.
                ok, error = self.crm_call(subscriber.contact_id, crm_add_field, crm_add_value)
                if not ok:
                    failed += 1
                    self.record_failure(failures_path, subscriber, "crm_add:%s" % crm_add_field, error)
                    self.stdout.write(self.style.ERROR("FAILED crm_add id=%d contact_id=%s: %s" % (subscriber.id, subscriber.contact_id, error)))
                    continue
                # Step 3 (CRM remove): same policy on failure.
                ok, error = self.crm_call(subscriber.contact_id, crm_remove_field, crm_remove_value)
                if not ok:
                    failed += 1
                    self.record_failure(failures_path, subscriber, "crm_remove:%s" % crm_remove_field, error)
                    self.stdout.write(self.style.ERROR("FAILED crm_remove id=%d contact_id=%s: %s" % (subscriber.id, subscriber.contact_id, error)))
                    continue
                migrated += 1
            else:
                cms_only_migrated += 1

            # Step 4 (CMS remove, last on purpose): leaving the source NL marks the subscriber as
            # fully migrated; everything before this line already succeeded.
            if reverse:
                subscriber.category_newsletters.remove(category)
            else:
                subscriber.newsletters.remove(publication)

            if options["sleep"]:
                time.sleep(options["sleep"])
            if options["progress_every"] and processed % options["progress_every"] == 0:
                self.stdout.write("... %d/%d processed (ok=%d, cms-only=%d, failed=%d)" % (processed, total, migrated, cms_only_migrated, failed))

        self.stdout.write(self.style.MIGRATE_HEADING("\nSummary"))
        self.stdout.write("Processed: %d" % processed)
        self.stdout.write("Migrated with CRM sync: %d" % migrated)
        self.stdout.write("Migrated CMS-only (no contact_id%s): %d" % (" or --cms-only" if cms_only else "", cms_only_migrated))
        if failed:
            self.stdout.write(self.style.ERROR("Failed: %d — details in %s" % (failed, failures_path)))
            self.stdout.write("Failed subscribers remain in the source newsletter: re-running the command retries only them.")
        else:
            self.stdout.write(self.style.SUCCESS("No failures."))
