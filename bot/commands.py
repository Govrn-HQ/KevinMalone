import logging
import discord
#import pyairtable
from config import read_file, GUILD_IDS
#from pyairtable import Api, Base, Table
#from pyairtable.formulas import match
#from helpers import chooseID


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

#api = Api(airtable_key)


@bot.slash_command(guild_id=GUILD_IDS, help="Send users link to report engagement")
async def report(ctx):
    if not ctx.guild:
        await ctx.response.send_message("Please run this command in a guild!")
        ctx.response.is_done()
    else:
        airtableLinks = read_file()
        airtableLink = airtableLinks.get(str(ctx.guild.id))

        if airtableLink:
            await bot.fetch_user(int(ctx.author.id))
            await ctx.response.send_message(
                f"Add contributions to the following airtable {airtableLink}",
                ephemeral=True,
            ).add_reaction("🐦")
            
            ctx.response.is_done()
        else:
            message = await ctx.response.send_message(
                "No airtable link was provided for this Discord server", ephemeral=True
            )
            await message.add_reaction("🐦")
            ctx.response.is_done()

# Onboarding a new user
"""@bot.slash_command(guild_id=GUILD_IDS, help="Send users link to report engagement")
async def start(ctx):
    if not ctx.guild:
        await ctx.response.send_message("Please run this command in a guild!")
        ctx.response.is_done()
    else:
        #check airtable to see if the member exists by matching the discordID to a discordID record in airtable.
        #userCurrent = table.all(formula=[match=ctx.author.id])
        #airtableLink = airtableLinks.get(str(ctx.guild.id))
        table = Table(airtable_key, mgd_base, 'Christine test')
        records = table.all(formula=match({'Discord ID': ctx.author.id}))
        current_user = len(records) > 0

        if current_user:
            await bot.fetch_user(int(ctx.author.id))
            await ctx.response.send_message(
                f"Welcome back!  It's great to see you again.  Did you want to update any of your ID information?",
                #@keeating what's the 'f' before the line for?
                ephemeral=True,
            )
            ctx.response.is_done()
        else:
            await ctx.response.send_message(
                "No airtable link was provided for this Discord server", ephemeral=True
            )
            ctx.response.is_done()"""
