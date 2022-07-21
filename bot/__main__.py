import logging
import sys
from bot.common.tasks.tasks import tasks

from bot.common.bot.bot import bot
import constants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting...")


def main():
    TOKEN = constants.Bot.token
    if TOKEN is None:
        sys.exit("Environment variable API_TOKEN must be supplied")
    tasks.start()
    bot.run(TOKEN)


main()
