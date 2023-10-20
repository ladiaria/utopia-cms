import time
from datetime import date
import smtplib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from libs.utils import smtp_server_choice, smtp_connect, smtp_quit
from dashboard.models import NewsletterDelivery


class NoSuitableServer(Exception):
    pass


class SendNLCommand(BaseCommand):

    retry_last_delivery, subscriber_sent, user_sent, smtp_servers = False, 0, 0, []

    def add_arguments(self, parser):
        parser.add_argument('subscriber_ids', nargs='*', type=int)
        parser.add_argument(
            '--no-deliver',
            action='store_true',
            default=False,
            dest='no_deliver',
            help='Do not send the emails, only log',
        )
        if getattr(self, "offline", True):
            parser.add_argument(
                '--offline',
                action='store_true',
                default=False,
                dest='offline',
                help='Do not use the database to fetch email data, get it from datasets previously generated',
            )
        if getattr(self, "as_news", True):
            parser.add_argument(
                '--as-news',
                action='store_true',
                default=False,
                dest='as_news',
                help='Send only to those who have "allow news" activated and are not subscribed to this newsletter',
            )
        if getattr(self, "export_subscribers", True):
            parser.add_argument(
                '--export-subscribers',
                action='store_true',
                default=False,
                dest='export_subscribers',
                help='Not send and export the subscribers dataset for offline usage later with the option --offline',
            )
        if getattr(self, "export_context", True):
            parser.add_argument(
                '--export-context',
                action='store_true',
                default=False,
                dest='export_context',
                help='Not send and export the context dataset for offline usage later with the option --offline',
            )
        parser.add_argument(
            '--starting-from-s',
            action='store',
            type=str,
            dest='starting_from_s',
            help='Send only to those subscribers whose email is alphabetically greater than this value',
        )
        parser.add_argument(
            '--starting-from-ns',
            action='store',
            type=str,
            dest='starting_from_ns',
            help='Send only to those non-subscribers whose email is alphabetically greater than this value',
        )
        parser.add_argument(
            '--partitions',
            action='store',
            type=int,
            dest='partitions',
            help='Used with --mod, divide receipts in this quantity of partitions e.g.: --partitions=5',
        )
        parser.add_argument(
            '--mod',
            action='store',
            type=int,
            dest='mod',
            help='When --partitions is set, only take receipts whose id MOD partitions == this value e.g.: --mod=0',
        )
        parser.add_argument(
            '--delay',
            action='store',
            default=0,
            type=float,
            dest='delay',
            help='Seconds to wait between deliveries, e.g. to wait 500 miliseconds: --delay=0.5',
        )

    def load_options(self, options):
        for arg in (
            'partitions',
            'mod',
            'offline',
            'export_subscribers',
            'export_context',
            'no_deliver',
            "as_news",
            'starting_from_s',
            'starting_from_ns',
            'subscriber_ids',
            'delay',
        ):
            if getattr(self, arg, True):
                setattr(self, arg, options.get(arg))
        self.export_only = self.export_subscribers or self.export_context
        if self.offline:
            if self.starting_from_s or self.starting_from_ns:
                raise CommandError('--starting-from* options for offline usage not yet implemented')
            if self.export_only:
                raise CommandError('--export-* options can not be used with --offline')
        if self.partitions is None and self.mod is not None or self.mod is None and self.partitions is not None:
            raise CommandError('--partitions must be used with --mod')

    def sendmail(self, s_user_email, log, msg, is_subscriber, s_id):
        send_result, smtp_index_choosed, mta_label = None, None, None
        try:
            if not self.no_deliver:
                smtp_index_choosed = smtp_server_choice(s_user_email, self.smtp_servers)
                if smtp_index_choosed is None:
                    raise NoSuitableServer(
                        "No suitable server available for %ssubscriber %s\t%s" % (
                            '' if is_subscriber else 'non-', s_id, s_user_email
                        )
                    )
                else:
                    mta_label = ("A%d" % smtp_index_choosed) if smtp_index_choosed else "M"
                    if self.delay:
                        time.sleep(self.delay)
                    # send using smtp to receive bounces in another mailbox.
                    # (for consistency, because this should be already covered by using the Return-Path header)
                    send_result = self.smtp_servers[smtp_index_choosed].sendmail(
                        settings.NEWSLETTERS_FROM_MX, [s_user_email], msg.as_string()
                    )
                assert not send_result
            log.info(
                "%sEmail %s to %ssubscriber %s\t%s" % (
                    "(mod %d) " % self.mod if self.mod is not None else "",
                    'simulated' if self.no_deliver else 'sent(%s)' % mta_label,
                    '' if is_subscriber else 'non-',
                    s_id,
                    s_user_email,
                )
            )
            if is_subscriber:
                self.subscriber_sent += 1
            else:
                self.user_sent += 1
        except NoSuitableServer as nss_exc:
            log.error(nss_exc.args[0])
            self.retry_last_delivery = False
        except AssertionError:
            # Retries are made only once per iteration to avoid possible infinite loop.
            self.retry_last_delivery = not self.retry_last_delivery
            log_message = "Delivery errors(%s) for %ssubscriber %s: %s" % (
                mta_label, '' if is_subscriber else 'non-', s_id, send_result
            )
            if self.retry_last_delivery:
                log.warning(log_message + ". Retrying ...")
            else:
                log.error(log_message + ". Retry failed, message not sent.")
        except smtplib.SMTPRecipientsRefused:
            # It's very probabbly that this is a local delivery to an unknown mailbox, it will not be retried.
            log.warning("Email refused for %ssubscriber %s\t%s" % ('' if is_subscriber else 'non-', s_id, s_user_email))
        except smtplib.SMTPServerDisconnected:
            # Retries are made only once per iteration for equality on other errors.
            # (avoid infinite loop on disconnections is caller's responsibility)
            self.retry_last_delivery = not self.retry_last_delivery
            log_message = "MTA(%s) down, email to %s not sent. Reconnecting " % (mta_label, s_user_email)
            log_message += "to retry ..." if self.retry_last_delivery else "for the next delivery ..."
            self.smtp_servers[smtp_index_choosed] = smtp_connect(smtp_index_choosed)
            if not self.smtp_servers[smtp_index_choosed]:
                log.error(log_message + ' MTA reconnect failed')
            else:
                (log.warning if self.retry_last_delivery else log.error)(log_message)
        except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError):
            # This means that is very probabble that this server will not work at all for any iteration, so we
            # will make it unavailable and retry this delivery (only once).
            self.retry_last_delivery = not self.retry_last_delivery
            log_message = "MTA(%s) error, email to %s not sent." % (mta_label, s_user_email)
            if self.retry_last_delivery:
                log.warning(log_message + " Will be retried using another server...")
            else:
                log.error(log_message)
            self.smtp_servers[smtp_index_choosed] = None
        else:
            self.retry_last_delivery = False

    def finish(self, log, newsletter_name=None):
        if not self.export_only:
            if not self.no_deliver:
                smtp_quit(self.smtp_servers)

            # update log stats counters only if subscriber_ids not given
            if newsletter_name and not self.subscriber_ids:
                try:
                    nl_delivery, created = NewsletterDelivery.objects.get_or_create(
                        delivery_date=date.today(), newsletter_name=newsletter_name
                    )
                    nl_delivery.user_sent = (nl_delivery.user_sent or 0) + self.user_sent
                    nl_delivery.subscriber_sent = (nl_delivery.subscriber_sent or 0) + self.subscriber_sent
                    nl_delivery.save()
                except Exception as e:
                    log.error('Delivery stats not updated: %s' % e)

            log.info(
                '%s%s stats: user_sent: %d, subscriber_sent: %d' % (
                    "(mod %d) " % self.mod if self.mod is not None else "",
                    'Simulation' if self.no_deliver else 'Delivery',
                    self.user_sent,
                    self.subscriber_sent,
                )
            )
            log.info(
                "%s%s completed in %.0f seconds" % (
                    "(mod %d) " % self.mod if self.mod is not None else "",
                    'Simulation' if self.no_deliver else 'Delivery',
                    time.time() - self.start_time,
                )
            )
