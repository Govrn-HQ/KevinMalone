import logging

from commands import bot
from exceptions import ErrorHandler

logger = logging.getLogger(__name__)


@bot.event
async def on_application_command_error(ctx, error):
    # All commands will be slash commands
    # Commands will be sent back from where they come from
    err = ErrorHandler(error)
    logger.infor(f"Command error type {type(error)}")
    await ctx.response.send_messge(err.msg)
    ctx.response.is_done()


bot.on_application_command_error = on_application_command_error
