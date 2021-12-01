import logging
import discord
from config import read_file, GUILD_IDS

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)


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
            )
            ctx.response.is_done()
        else:
            await ctx.response.send_message(
                "No airtable link was provided for this Discord server", ephemeral=True
            )
            ctx.response.is_done()
