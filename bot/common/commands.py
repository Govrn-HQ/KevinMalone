from distutils.util import strtobool
import json
import logging
import discord
import hashlib
import constants

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)


from common.core import bot  # noqa: E402
from common.airtable import (  # noqa: E402
    find_user,
    create_user,
    get_discord_record,
    get_guild,
)
from common.threads.thread_builder import (  # noqa: E402
    build_cache_value,
    ThreadKeys,
)
from common.threads.onboarding import Onboarding  # noqa: E402
from common.threads.update import UpdateProfile  # noqa: E402
from config import (  # noqa: E402
    read_file,
    GUILD_IDS,
    INFO_EMBED_COLOR,
    Redis,
    get_list_of_emojis,
)
from exceptions import NotGuildException  # noqa: E402
from exceptions import ErrorHandler  # noqa: E402


logger = logging.getLogger(__name__)


def get_thread(user_id, key):
    val = json.loads(key)
    thread = val.get("thread")
    step = val.get("step")
    message_id = val.get("message_id")
    guild_id = val.get("guild_id")
    if thread == ThreadKeys.ONBOARDING.value:
        return Onboarding(user_id, step, message_id, guild_id)
    elif thread == ThreadKeys.UPDATE_PROFILE.value:
        return UpdateProfile(user_id, step, message_id, guild_id)
    raise Exception("Unknown Thread!")


@bot.slash_command(
    guild_id=GUILD_IDS, description="Send users link to report engagement",
)
async def report(ctx):
    is_guild = bool(ctx.guild)
    if not is_guild:
        raise NotGuildException("Command was executed outside of a guild")

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


if bool(strtobool(constants.Bot.is_dev)):

    @bot.slash_command(guild_id=GUILD_IDS, description="Get started with Govern")
    async def join(ctx):
        is_guild = bool(ctx.guild)
        if not is_guild:
            raise NotGuildException("Command was executed outside of a guild")

        is_user = await find_user(ctx.author.id, ctx.guild.id)
        if is_user:
            # Send welcome message and
            # And ask what journey they are
            # on by sending all the commands
            application_commands = bot.application_commands
            embed = discord.Embed(
                colour=INFO_EMBED_COLOR, title="Welcome Back", description="",
            )
            for cmd in application_commands:
                if isinstance(cmd, discord.SlashCommand):
                    embed.add_field(
                        name=f"/ {cmd.name}", value=cmd.description, inline=False
                    )
            await ctx.response.send_message(embed=embed, ephemeral=True)
            ctx.response.is_done()
            return

        await ctx.response.defer()
        # store guild_id and disord_id
        await create_user(ctx.author.id, ctx.guild.id)
        # check if user can be DMed
        can_send_message = ctx.can_send(discord.Message)
        if not can_send_message:
            await ctx.followup.send(
                "I cannot onboard you. Please turn on DM's from this server!"
            )
            return

        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            title="Welcome",
            description="Thank you for joining the Govrn ecosystem! "
            "To help automate  gathering your contributions to {ctx.guild.name} "
            "we need you to provide some information. Any of the following data "
            "requests can be skipped with the ⏭️  emoji!",
        )
        logger.info(
            f"Key: {build_cache_value(ThreadKeys.ONBOARDING.value, '', ctx.guild.id)}"
        )
        message = await ctx.author.send(embed=embed)
        await Onboarding(
            ctx.author.id,
            hashlib.sha256("".encode()).hexdigest(),
            message.id,
            ctx.guild.id,
        ).send(message)
        await ctx.followup.send("Check your Dms to continue onboarding", ephemeral=True)

    @bot.slash_command(
        guild_id=GUILD_IDS, description="Update your profile for a given Dao"
    )
    async def update(ctx):
        is_guild = bool(ctx.guild)
        if is_guild:
            return
        else:
            discord_rec = await get_discord_record(ctx.author.id)
            airtable_guild_ids = discord_rec.get("fields").get("guild_id")
            if not airtable_guild_ids:
                embed = discord.Embed(
                    colour=INFO_EMBED_COLOR,
                    description="Cannot update profile because you "
                    "have not been onboarded to any daos. Run /join in the "
                    "discord you want to onboard to",
                )
                await ctx.response.send_message(embed=embed)
                ctx.response.is_done()
                return

            await ctx.response.defer()
            guild_ids = []
            for record_id in airtable_guild_ids:
                g = await get_guild(record_id)
                guild_id = g.get("guild_id")
                if guild_id:
                    guild_ids.append(guild_id)
            embed = discord.Embed(
                colour=INFO_EMBED_COLOR,
                title="Welcome",
                description="Which profile guild would you like to update?",
            )
            emojis = get_list_of_emojis(len(guild_ids))
            daos = {}
            for idx, guild_id in enumerate(guild_ids):
                guild = await bot.fetch_guild(guild_id)
                if not guild:
                    continue
                emoji = emojis[idx]
                daos[emoji] = guild.id
                embed.add_field(name=guild.name, value=emoji)
            message = await ctx.followup.send(embed=embed)
            for emoji in emojis:
                await message.add_reaction(emoji)
            await Redis.set(
                ctx.author.id,
                build_cache_value(
                    ThreadKeys.UPDATE_PROFILE.value,
                    UpdateProfile().steps.hash_,
                    "",
                    message.id,
                    metadata={"daos": daos},
                ),
            )


# Event listners
@bot.event
async def on_application_command_error(ctx, exception):
    err = ErrorHandler(exception)
    logger.info(f"Command error type {type(exception)}")
    await ctx.response.send_message(err.msg)
    ctx.response.is_done()


@bot.event
async def on_message(message):
    if message.author.bot is True:
        return

    # Check channel DM channel
    if not isinstance(message.channel, discord.DMChannel):
        return

    # Check if user has open thread
    thread_key = await Redis.get(message.author.id)
    if not thread_key:
        # TODO: It may make sense to send some sort of message here
        return

    thread = get_thread(message.author.id, thread_key)
    await thread.send(message)


@bot.event
async def on_raw_reaction_add(payload):
    from commands import bot

    reaction = payload
    user = await bot.fetch_user(int(payload.user_id))
    channel = await bot.fetch_channel(int(reaction.channel_id))
    if user.bot is True:
        return

    # Check channel DM channel
    if not isinstance(channel, discord.DMChannel):
        return

    # Check if user has open thread
    thread_key = await Redis.get(user.id)
    if not thread_key:
        # TODO: It may make sense to send some sort of message here
        return

    thread = get_thread(user.id, thread_key)
    await thread.handle_reaction(reaction, user)


bot.on_application_command_error = on_application_command_error
