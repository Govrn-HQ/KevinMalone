from discord.ext import commands

from .exceptions import NotGuildException


def is_guild_msg():
    async def predicate(ctx):
        is_guild = bool(ctx.guild)
        if not is_guild:
            raise NotGuildException("Command was executed outside of a guild")
        return True

    return commands.check(predicate)
