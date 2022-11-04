import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)


def error_log(exception):
    logger.error(exception)
