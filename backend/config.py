import os

import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

ANTHROPIC_TOKEN = os.getenv("ANTHROPIC_TOKEN")