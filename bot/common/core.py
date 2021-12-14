import discord

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

import common.commands
