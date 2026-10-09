#!/usr/bin/env python3

# Blackboard MCP Server
#
#   Requirements
#       Python 3.10+
#       mcp >= 2.x
#
#   Environment variables:
#       BLACKBOARD_DB
#       BLACKBOARD_LOG_LEVEL
#       BLACKBOARD_MAX_CONTENT_SIZE
#       BLACKBOARD_MAX_COMMENT_SIZE
#       BLACKBOARD_MAX_PROMPT_SIZE

import sys
import mcp
import logging
import bbmcps_cfg as cfg
import bbmcps_fn as fn

def main():

    fn.setupLogging()
    logging.info(
        "%s %s starting",
        cfg.SERVER_NAME,
        cfg.SERVER_VERSION,
    )

    logging.info(
        "Python MCP package version: %s",
        getattr(mcp, "__version__", "2.0"),
    )

    logging.info(
        "Database: %s",
        cfg.DB_PATH,
    )

    fn.get_srv().run(transport="stdio")

