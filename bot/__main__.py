import logging
import os
import sys

from dotenv import load_dotenv
from commands import bot

load_dotenv()

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
logger.info("Starting...")


def main():
    TOKEN = os.getenv("API_TOKEN")
    if TOKEN is None:
        sys.exit("Environment variable API_TOKEN must be supplied")
    bot.run(TOKEN)


main()
