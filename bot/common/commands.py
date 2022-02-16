from bot import constants
from discord.commands import Option
from distutils.util import strtobool
import logging
import hashlib
import discord


from bot.common.airtable import (
    find_user,
    create_user,
    get_discord_record,
    get_guild,
)
from bot.common.bot.bot import bot
from bot.common.threads.thread_builder import (
    build_cache_value,
    ThreadKeys,
)
from bot.common.threads.onboarding import Onboarding
from bot.common.threads.report import ReportStep
from bot.common.threads.points import DisplayPointsStep
from bot.common.threads.update import UpdateProfile
from bot.config import (
    read_file,
    GUILD_IDS,
    INFO_EMBED_COLOR,
    Redis,
    get_list_of_emojis,
)
from bot.exceptions import NotGuildException, ErrorHandler
from bot.common.guild_select import get_thread, GuildSelect


logger = logging.getLogger(__name__)


@bot.slash_command(
    guild_id=GUILD_IDS,
    description="Send users link to report engagement",
)
async def report(ctx):
    is_guild = bool(ctx.guild)
    if not is_guild:
        # Open report thread
        # which will send either of the below messages
        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description="Which community would you like to report a contribution to?",
        )
        error_embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description="You are not a par of any communities. "
            "Please run the /join command in a guild you are in",
        )

        message, metadata = await select_guild(ctx, embed, error_embed)
        thread = await GuildSelect(
            ctx.author.id,
            hashlib.sha256("".encode()).hexdigest(),
            message.id,
            "",
        )
        # TODO add thread and step
        return await Redis.set(
            ctx.author.id,
            build_cache_value(
                ThreadKeys.GUILD_SELECT.value,
                thread.steps.hash_,
                "",
                message.id,
                metadata={
                    **metadata,
                    "thread_name": ThreadKeys.REPORT.value,
                },
            ),
        )

    airtableLinks = read_file()
    airtableLink = airtableLinks.get(str(ctx.guild.id))

    if airtableLink:
        _, metadata = await ReportStep(
            guild_id=ctx.guild.id, cache=Redis, bot=bot, channel=ctx.channel
        ).send(None, ctx.author.id)
        # send message to congrats channel

        await ctx.response.send_message(metadata.get("msg"), ephemeral=True)
    else:
        await ctx.response.send_message(
            "No airtable link was provided for this Discord server", ephemeral=True
        )


@bot.slash_command(
    guild_id=GUILD_IDS,
    description="Send user points for a given community",
)
async def points(
    ctx,
    days: Option(
        str,
        "Days of contribution",  # noqa: F722
        choices=["1", "7", "30", "90", "180", "365", "all"],
    ),
):
    is_guild = bool(ctx.guild)
    if not is_guild:
        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description="Which community would you like to get a list of engagements?",
        )
        error_embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description="You are not a part of any communities. "
            "Please run the /points command in a guild you are in",
        )

        message, metadata = await select_guild(ctx, embed, error_embed)
        thread = await GuildSelect(
            ctx.author.id,
            hashlib.sha256("".encode()).hexdigest(),
            message.id,
            "",
        )
        return await Redis.set(
            ctx.author.id,
            build_cache_value(
                ThreadKeys.GUILD_SELECT.value,
                thread.steps.hash_,
                "",
                message.id,
                metadata={
                    **metadata,
                    "thread_name": ThreadKeys.POINTS.value,
                    "days": days,
                },
            ),
        )

    _, metadata = await DisplayPointsStep(
        guild_id=ctx.guild.id, cache=Redis, bot=bot, channel=ctx.channel, days=days
    ).send(None, ctx.author.id)

    await ctx.response.send_message(metadata.get("msg"), ephemeral=True)


@bot.slash_command(guild_id=GUILD_IDS, description="Get started with Govrn")
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
            colour=INFO_EMBED_COLOR,
            title="Welcome Back",
            description="",
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

    embed = discord.Embed(
        colour=INFO_EMBED_COLOR,
        title="Welcome",
        description="Welcome to the Govrn Ecosystem!  "
        "We're excited to have you part of our movement."
        "To help automate the gathering of your contributions"
        f" to {ctx.guild.name} we need some information."
        "We use your IDs to automatically pull your contributions for you to "
        f"easily submit to {ctx.guild.name}. "
        "You can skip any requests by using the ⏭️  emoji!",
    )
    logger.info(
        f"Key: {build_cache_value(ThreadKeys.ONBOARDING.value, '', ctx.guild.id)}"
    )
    try:

        message = await ctx.author.send(embed=embed)
    except discord.Forbidden:
        message = await ctx.followup.send(
            "Please enable DM's in order to use the Govrn Bot!", ephemeral=True
        )
        return

    await create_user(ctx.author.id, ctx.guild.id)
    onboarding = await Onboarding(
        ctx.author.id,
        hashlib.sha256("".encode()).hexdigest(),
        message.id,
        ctx.guild.id,
    )
    await onboarding.send(message)
    await ctx.followup.send("Check your DM's to continue onboarding", ephemeral=True)


@bot.slash_command(
    guild_id=GUILD_IDS, description="Update your profile for a given community"
)
async def update(ctx):
    is_guild = bool(ctx.guild)
    if is_guild:
        await ctx.respond("Please run this command in a DM channel", ephemeral=True)
        return
    else:
        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            title="Welcome",
            description="Which community profile would you like to update?",
        )
        error_embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description="I cannot update profile because you "
            "have not been onboarded for any communities. Run /join in the "
            "discord you want to join!",
        )

        message, metadata = await select_guild(ctx, embed, error_embed)
        if not metadata:
            return
        thread = await UpdateProfile(
            ctx.author.id,
            hashlib.sha256("".encode()).hexdigest(),
            message.id,
            "",
        )
        await Redis.set(
            ctx.author.id,
            build_cache_value(
                ThreadKeys.UPDATE_PROFILE.value,
                thread.steps.hash_,
                "",
                message.id,
                metadata=metadata,
            ),
        )


if bool(strtobool(constants.Bot.is_dev)):

    @bot.slash_command(
        guild_id=GUILD_IDS, description="Add first contributions to the guild"
    )
    async def add_onboarding_contributions(ctx):
        is_guild = bool(ctx.guild)
        if is_guild:
            await ctx.respond("Please run this command in a DM channel", ephemeral=True)
            return
        else:
            embed = discord.Embed(
                colour=INFO_EMBED_COLOR,
                title="Contributions",
                description="Which community would you like to add your "
                "initial contributions to?",
            )
            error_embed = discord.Embed(
                colour=INFO_EMBED_COLOR,
                description="I cannot add any contributions because you "
                "have not been onboarded for any communities. Run /join in the "
                "discord you want to join!",
            )
            message, metadata = await select_guild(ctx, embed, error_embed)
            if not metadata:
                return
            thread = await GuildSelect(
                ctx.author.id,
                hashlib.sha256("".encode()).hexdigest(),
                message.id,
                "",
            )
            await Redis.set(
                ctx.author.id,
                build_cache_value(
                    ThreadKeys.GUILD_SELECT.value,
                    thread.steps.hash_,
                    "",
                    message.id,
                    metadata={
                        **metadata,
                        "thread_name": ThreadKeys.INITIAL_CONTRIBUTIONS.value,
                    },
                ),
            )


async def select_guild(ctx, response_embed, error_embed):
    discord_rec = await get_discord_record(ctx.author.id)
    airtable_guild_ids = discord_rec.get("fields").get("guild_id")
    if not airtable_guild_ids:
        await ctx.response.send_message(embed=error_embed)
        ctx.response.is_done()
        return None, None

    await ctx.response.defer()
    guild_ids = []
    for record_id in airtable_guild_ids:
        g = await get_guild(record_id)
        guild_id = g.get("guild_id")
        if guild_id:
            guild_ids.append(guild_id)
    embed = response_embed
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
    return message, {"daos": daos}


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

    thread = await get_thread(message.author.id, thread_key)
    await thread.send(message)


@bot.event
async def on_raw_reaction_add(payload):
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

    thread = await get_thread(user.id, thread_key)
    await thread.handle_reaction(reaction, user)


bot.on_application_command_error = on_application_command_error
