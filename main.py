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

import logging

def main():

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s: "
            "%(message)s"
        ),
        stream=sys.stderr,
    )

    logger = logging.getLogger("blackboard")

    logger.info(
        "%s %s starting",
        SERVER_NAME,
        SERVER_VERSION,
    )

    logger.info(
        "Python MCP package version: %s",
        getattr(mcp, "__version__", "2.0"),
    )

    logger.info(
        "Database: %s",
        DB_PATH,
    )

    # stdout belongs to the MCP protocol.
    # Diagnostics must therefore go to stderr.
    blackboard.run(
        transport="stdio"
    )

