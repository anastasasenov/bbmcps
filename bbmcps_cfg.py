#BBMCPS

SERVER_NAME = "Blackboard MCP Server"
SERVER_VERSION = "1.0.0"

DEFAULT_DB = "blackboard.db"

DB_PATH = Path(
    os.environ.get("BLACKBOARD_DB", DEFAULT_DB)
).expanduser().resolve()

LOG_LEVEL = os.environ.get(
    "BLACKBOARD_LOG_LEVEL",
    "INFO"
).upper()

MAX_TOPIC_SIZE = 512

MAX_CONTENT_SIZE = int(
    os.environ.get(
        "BLACKBOARD_MAX_CONTENT_SIZE",
        str(1024 * 1024)
    )
)

MAX_COMMENT_SIZE = int(
    os.environ.get(
        "BLACKBOARD_MAX_COMMENT_SIZE",
        str(1024 * 1024)
    )
)

MAX_PROMPT_SIZE = int(
    os.environ.get(
        "BLACKBOARD_MAX_PROMPT_SIZE",
        str(1024 * 1024)
    )
)

MAX_URL_SIZE = 4096

MAX_SEARCH_RESULTS = 1000

SCHEMA_VERSION = 3
