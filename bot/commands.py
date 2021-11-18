from discord.ext import commands
from config import read_file

bot = commands.Bot(command_prefix="!")


@bot.group(help="All commands for kevin malone")
async def malone(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Subcommand {ctx.subcommand_passed} is not a valid subcommand!")


@malone.command(help="Send users link to report engagement")
async def report(ctx):
    airtableLinks = read_file()
    airtableLink = airtableLinks.get(str(ctx.guild.id))
    if airtableLink:
        user = await bot.fetch_user(int(ctx.author.id))
        await user.send(f"Add contributions to the following airtable {airtableLink}")
    else:
        await ctx.send("No airtable link was provided for this Discord server")
