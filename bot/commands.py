import discord
from config import read_file, GUILD_IDS

bot = discord.Bot()


@bot.slash_command(guild_id=GUILD_IDS, help="Send users link to report engagement")
async def report(ctx):
    airtableLinks = read_file()
    airtableLink = airtableLinks.get(str(ctx.guild_id))
    if not ctx.guild_id:
        await ctx.respond("Please run command in a guild!")
    elif airtableLink:
        user = await bot.fetch_user(int(ctx.user.id))
        await ctx.respond(f"Add contributions to the following airtable {airtableLink}")
    else:
        await ctx.respond("No airtable link was provided for this Discord server")
