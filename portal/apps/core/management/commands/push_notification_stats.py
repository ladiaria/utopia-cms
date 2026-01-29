import re
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import DeviceSubscribed, PushNotification


class Command(BaseCommand):
    help = """
        Shows push notification statistics from logs and database.

        Usage:
            ./manage.py push_notification_stats --last 7
            ./manage.py push_notification_stats --date 2026-01-29
            ./manage.py push_notification_stats --summary

        Example output:

            === DATABASE STATS ===

            Total subscribed devices: 2035
            Total push notifications created: 45
              - Sent: 42
              - Pending: 3

            === LOG FILE STATS ===

            Log file: /var/log/utopiacms/push_notifications.log
            Total log lines: 1523

            Send operations found: 42 (last 7 days)

            Timestamp            Tag             Sent    Failed    Total
            -----------------------------------------------------------------
            2026-01-28 10:30:45  article_123     2000        35     2035
            2026-01-28 15:22:10  article_456     1998        37     2035
            ...

            === SUMMARY ===

            Total send operations: 42
            Total notifications sent successfully: 84000
            Total notifications failed: 1470
            Success rate: 98.3%
            Total errors in log: 1470
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--last',
            type=int,
            default=None,
            help='Show stats for the last N days (default: 7)',
        )
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Show stats for a specific date (format: YYYY-MM-DD)',
        )
        parser.add_argument(
            '--summary',
            action='store_true',
            help='Show only summary (total devices, total notifications sent)',
        )
        parser.add_argument(
            '--log-file',
            dest='log_file',
            type=str,
            default=None,
            help='Path to log file (default: from settings.CORE_PUSH_NOTIFICATIONS_LOGFILE)',
        )

    def handle(self, *args, **options):
        log_file = options.get('log_file') or getattr(
            settings, 'CORE_PUSH_NOTIFICATIONS_LOGFILE', None
        )

        # Database stats
        self.stdout.write(self.style.HTTP_INFO('\n=== DATABASE STATS ===\n'))

        total_devices = DeviceSubscribed.objects.count()
        total_notifications = PushNotification.objects.count()
        sent_notifications = PushNotification.objects.filter(sent__isnull=False).count()
        pending_notifications = PushNotification.objects.filter(sent__isnull=True).count()

        self.stdout.write(f'Total subscribed devices: {total_devices}')
        self.stdout.write(f'Total push notifications created: {total_notifications}')
        self.stdout.write(f'  - Sent: {sent_notifications}')
        self.stdout.write(f'  - Pending: {pending_notifications}')

        if options.get('summary'):
            return

        # Log file stats
        self.stdout.write(self.style.HTTP_INFO('\n=== LOG FILE STATS ===\n'))

        if not log_file:
            self.stdout.write(self.style.WARNING(
                'CORE_PUSH_NOTIFICATIONS_LOGFILE not configured in settings'
            ))
            return

        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Log file not found: {log_file}'))
            return
        except PermissionError:
            self.stdout.write(self.style.ERROR(f'Permission denied reading: {log_file}'))
            return

        self.stdout.write(f'Log file: {log_file}')
        self.stdout.write(f'Total log lines: {len(lines)}\n')

        # Parse log entries
        # Format: "2026-01-29 10:30:45 INFO: Send results (tag, #sent-ok, #sent-failed): 'tag123', 2000, 35"
        send_results_pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) INFO: Send results \(tag, #sent-ok, #sent-failed\): '([^']*)', (\d+), (\d+)"
        )
        error_pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ERROR:"
        )

        # Filter by date if specified
        date_filter = None
        if options.get('date'):
            try:
                date_filter = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        elif options.get('last'):
            days = options['last']
            date_filter = (datetime.now() - timedelta(days=days)).date()

        results = []
        total_sent = 0
        total_failed = 0
        error_count = 0

        for line in lines:
            # Count errors
            error_match = error_pattern.match(line)
            if error_match:
                error_date = datetime.strptime(error_match.group(1), '%Y-%m-%d %H:%M:%S').date()
                if date_filter is None or error_date >= date_filter:
                    error_count += 1

            # Parse send results
            match = send_results_pattern.match(line)
            if match:
                timestamp_str, tag, sent, failed = match.groups()
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

                if date_filter is None or timestamp.date() >= date_filter:
                    results.append({
                        'timestamp': timestamp,
                        'tag': tag,
                        'sent': int(sent),
                        'failed': int(failed),
                    })
                    total_sent += int(sent)
                    total_failed += int(failed)

        if not results:
            filter_desc = ''
            if options.get('date'):
                filter_desc = f" for date {options['date']}"
            elif options.get('last'):
                filter_desc = f" in the last {options['last']} days"
            self.stdout.write(self.style.WARNING(f'No send results found in logs{filter_desc}'))
            return

        # Display results
        filter_desc = ''
        if options.get('date'):
            filter_desc = f" (date: {options['date']})"
        elif options.get('last'):
            filter_desc = f" (last {options['last']} days)"

        self.stdout.write(self.style.SUCCESS(f'Send operations found: {len(results)}{filter_desc}\n'))

        # Table header
        self.stdout.write(f"{'Timestamp':<20} {'Tag':<15} {'Sent':>8} {'Failed':>8} {'Total':>8}")
        self.stdout.write('-' * 65)

        for r in results[-20:]:  # Show last 20 entries
            total = r['sent'] + r['failed']
            self.stdout.write(
                f"{r['timestamp'].strftime('%Y-%m-%d %H:%M:%S'):<20} "
                f"{r['tag'][:15]:<15} "
                f"{r['sent']:>8} "
                f"{r['failed']:>8} "
                f"{total:>8}"
            )

        if len(results) > 20:
            self.stdout.write(f'\n... showing last 20 of {len(results)} entries')

        # Summary
        self.stdout.write(self.style.HTTP_INFO('\n=== SUMMARY ===\n'))
        self.stdout.write(f'Total send operations: {len(results)}')
        self.stdout.write(f'Total notifications sent successfully: {self.style.SUCCESS(str(total_sent))}')
        self.stdout.write(f'Total notifications failed: {self.style.ERROR(str(total_failed))}')
        if total_sent + total_failed > 0:
            success_rate = (total_sent / (total_sent + total_failed)) * 100
            self.stdout.write(f'Success rate: {success_rate:.1f}%')
        self.stdout.write(f'Total errors in log: {error_count}')