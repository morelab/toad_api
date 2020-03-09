import logging


# define VERBOSE only if it wasn't defined before importing this file
verbose = None
if "VERBOSE" in globals():
    verbose = globals().get("VERBOSE")
VERBOSE = verbose


# configure logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def log_info(msg):
    logger.info(msg)


def log_error(msg):
    logger.error(msg)


def log_info_verbose(msg):
    if VERBOSE:
        logger.info(msg)


def log_error_verbose(msg):
    if VERBOSE:
        logger.error(msg)
