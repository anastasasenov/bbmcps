#BBMCPS

import os
from pathlib import Path

SERVER_NAME = "Blackboard MCP Server"
SERVER_VERSION = "1.0.0"
DEFAULT_DB = "blackboard.db"
MAX_TOPIC_SIZE = 512
MAX_URL_SIZE = 4096
MAX_SEARCH_RESULTS = 1000
SCHEMA_VERSION = 3

DB_PATH = Path(
    os.environ.get("BBMCPS_DB", DEFAULT_DB)
).expanduser().resolve()

LOG_LEVEL = os.environ.get(
    "BBMCPS_LOG_LEVEL",
    "INFO"
).upper()

LOG_FILE = os.environ.get(
    "BBMCPS_LOG_FILE",
    "/tmp/bbmcps.log"
)

SERVER_STDIO = os.environ.get(
    "BBMCPS_SERVER_STDIO",
    ""
)

SERVER_HOST = os.environ.get(
    "BBMCPS_SERVER_HOST",
    "0.0.0.0"
)

SERVER_PORT = os.environ.get(
    "BBMCPS_SERVER_PORT",
    "8083"
)

MAX_CONTENT_SIZE = int(
    os.environ.get(
        "BBMCPS_MAX_CONTENT_SIZE",
        str(1024 * 1024)
    )
)

MAX_COMMENT_SIZE = int(
    os.environ.get(
        "BBMCPS_MAX_COMMENT_SIZE",
        str(1024 * 1024)
    )
)

MAX_PROMPT_SIZE = int(
    os.environ.get(
        "BBMCPS_MAX_PROMPT_SIZE",
        str(1024 * 1024)
    )
)
