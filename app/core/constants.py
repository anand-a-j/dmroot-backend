APP_NAME = "DMRoot"

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# General request limits
DEFAULT_REQUEST_TIMEOUT = 30

# Background processing
DEFAULT_MAX_RETRIES = 3

# Password policy (max length stops huge inputs from burning CPU in Argon2)
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128