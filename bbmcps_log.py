# BBMCPS

import logging
import bbmcps_cfg as cfg

def get_logger():

    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, cfg.LOG_LEVEL, "INFO"))
    h = logging.StreamHandler()
    h.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(h)

    return logger
