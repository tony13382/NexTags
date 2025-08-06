import os

import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

ANTHROPIC_TOKEN = os.getenv("ANTHROPIC_TOKEN")
JELLYFIN_HOST = os.getenv("JELLYFIN_HOST")
JELLYFIN_USER_ID = os.getenv("JELLYFIN_USER_ID")
JELLYFIN_USER_NAME = os.getenv("JELLYFIN_USER_NAME")
JELLYFIN_USER_PW = os.getenv("JELLYFIN_USER_PW")