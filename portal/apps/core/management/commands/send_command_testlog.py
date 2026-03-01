import logging

from django.conf import settings

from . import SendNLCommand


LOG_SUFFIX = 'send_command_testlog'


class Command(SendNLCommand):
    help = 'Test the log file creation'

    def handle(self, *args, **options):
        self.load_options(options)
        verbosity = options.get('verbosity')
        log = logging.getLogger(__name__)
        self.initlog(log, LOG_SUFFIX)

        print("DEBUG is", settings.DEBUG)
        print("verbosity is", verbosity)
        print("the lines you saw below should be consistent with the DEBUG and verbosity values\n")

        if settings.DEBUG:
            log.debug('debug line i should viewing it because DEBUG is True, no matter the verbosity level')
            log.info('info line i should viewing it because DEBUG is True, no matter the verbosity level')
            log.warning('warning line i should viewing it because DEBUG is True, no matter the verbosity level')
        else:
            log.debug('debug line i should not viewing it because DEBUG is False, no matter the verbosity level')
            if verbosity > 1:
                log.info('info line i should viewing it because verbosity > 1, no matter the DEBUG value')
                log.warning('warning line i should viewing it because verbosity > 1, no matter the DEBUG value')
            else:
                log.info('info line i should not viewing it because DEBUG is False and verbosity <= 1')
                log.warning('warning line i should not viewing it because DEBUG is False and verbosity <= 1')
        log.error('error line i should viewing it despite of DEBUG value')
        log.critical('critical line i should viewing it despite of DEBUG value')

        print(
            """

            now make a tail -20 of the log file and you should see only 1 line for all the levels of logging plus or
            minus debug lines if DEBUG is True or False respectively, run this to check it:

            tail -20 %s

            ********************************
            """ % (settings.SENDNEWSLETTER_LOGFILE % (LOG_SUFFIX, ""))
        )
