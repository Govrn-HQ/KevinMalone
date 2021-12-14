import discord

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

import common.commands  # noqa: E40, F401
