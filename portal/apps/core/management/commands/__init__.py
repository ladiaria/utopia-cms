import sys
import time
import logging
from datetime import datetime
import smtplib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from libs.utils import smtp_server_choice, smtp_connect, smtp_quit
from dashboard.models import NewsletterDelivery


class NoSuitableServer(Exception):
    pass


class SendNLCommand(BaseCommand):

    retry_last_delivery, ignore_on_retrying, subscriber_sent, user_sent, smtp_servers = False, None, 0, 0, []

    def add_arguments(self, parser):
        parser.add_argument('subscriber_ids', nargs='*', type=int)
        parser.add_argument(
            '--no-deliver',
            action='store_true',
            default=False,
            dest='no_deliver',
            help='Do not send the emails, only log',
        )
        parser.add_argument(
            '--no-logfile',
            action='store_true',
            default=False,
            dest='no_logfile',
            help='Do not log to any file, log only to stdout and stderr',
        )
        parser.add_argument(
            '--no-update-stats',
            action='store_true',
            default=False,
            dest='no_update_stats',
            help='Do not update or create any delivery stats objects',
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
            "no_logfile",
            "no_update_stats",
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
        self.nl_delivery_dt = datetime.now()

    def initlog(self, log, substitution_prefix):
        log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', '%H:%M:%S')
        log.setLevel(logging.DEBUG)
        # print also errors to stderr to receive cron alert
        err_handler = logging.StreamHandler(sys.stderr)
        err_handler.setLevel(logging.ERROR)
        err_handler.setFormatter(log_formatter)
        log.addHandler(err_handler)
        if not self.export_only and not self.no_logfile:
            h = logging.FileHandler(
                filename=settings.SENDNEWSLETTER_LOGFILE % (
                    substitution_prefix + ("_as_news" if self.as_news else ""), self.nl_delivery_dt.strftime('%Y%m%d'),
                )
            )
            h.setFormatter(log_formatter)
            log.addHandler(h)

    def sendmail(self, s_user_email, log, msg, is_subscriber, s_id):
        send_result, smtp_index_choosed, mta_label = None, None, None
        try:
            if not self.no_deliver:
                choice_kwargs = {}
                if self.retry_last_delivery and self.ignore_on_retrying:
                    # if there is a server index to be ignored, set it now
                    choice_kwargs["ignore_from_available"] = self.ignore_on_retrying
                smtp_index_choosed = smtp_server_choice(s_user_email, self.smtp_servers, **choice_kwargs)
                self.ignore_on_retrying = None  # blank possible ignore on retrying index used
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
            log.warning(
                "Email refused for %ssubscriber %s\t%s" % ('' if is_subscriber else 'non-', s_id, s_user_email)
            )
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
        except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as smtp_exc:
            # This means that is very probabble that this server will not work at all for any iteration, so we
            # will make it unavailable (on most conditions, see last if here) and retry this delivery (only once).
            self.retry_last_delivery = not self.retry_last_delivery
            log_message = "MTA(%s) error, email to %s not sent." % (mta_label, s_user_email)
            if self.retry_last_delivery:
                log.warning(log_message + " Will be retried using another server...")
            else:
                log.error(log_message)
            if type(smtp_exc) is smtplib.SMTPSenderRefused and smtp_exc.smtp_code == 552:
                # msg size err. (if that is the case, the server is still working but this message is too large for it)
                # we must ignore the server in the retry attempt, if such.
                if self.retry_last_delivery:
                    self.ignore_on_retrying = smtp_index_choosed
            else:
                self.smtp_servers[smtp_index_choosed] = None
        else:
            self.retry_last_delivery = False

    def finish(self, log, newsletter_name=None):
        if not self.export_only:
            if not self.no_deliver:
                smtp_quit(self.smtp_servers)

            # update log stats counters only if subscriber_ids not given and not called with --no-update-stats
            if newsletter_name and not self.subscriber_ids and not self.no_update_stats:
                try:
                    nl_delivery, created = NewsletterDelivery.objects.get_or_create(
                        delivery_date=self.nl_delivery_dt.date(), newsletter_name=newsletter_name
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
                    time.time() - self.nl_delivery_dt.timestamp(),
                )
            )
