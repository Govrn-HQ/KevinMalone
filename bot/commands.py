import logging
import discord
from discord.ext import commands
from config import read_file, GUILD_IDS
import constants

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(intents=intents)

@bot.slash_command(guild_id=GUILD_IDS, help="Send users link to report engagement")
async def report(ctx):
    airtableLinks = read_file()
    airtableLink = airtableLinks.get(str(ctx.guild.id))
    if not ctx.guild.id:
        await ctx.respond("Please run command in a guild!")
    elif airtableLink:
        await bot.fetch_user(int(ctx.author.id))
        await ctx.send(f"Add contributions to the following airtable {airtableLink}")
    else:
        await ctx.send("No airtable link was provided for this Discord server")
