import logging
import sys
from commands import bot
import constants

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.info("Starting...")


def main():
    TOKEN = constants.Bot.token
    if TOKEN is None:
        sys.exit("Environment variable API_TOKEN must be supplied")
    bot.run(TOKEN)
   

main()
