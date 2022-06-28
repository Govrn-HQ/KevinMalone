import logging

from bot.common.threads.thread_builder import (
    BaseThread,
    ThreadKeys,
    BaseStep,
    StepKeys,
    Step,
)
from bot.common.graphql import (
    fetch_user,
    get_guild,
    create_guild,
    update_guild_name
)
from bot.common.threads.thread_builder import (
    write_cache_metadata,
    get_cache_metadata_key,
)
from bot.exceptions import ThreadTerminatingException
# from bot.common.threads.utils import (  # noqa: E402
# set_thread_and_send
# )

logger = logging.getLogger(__name__)


class AddDaoPromptId(BaseStep):
    """Prompts the user to input the discord ID of the guild they wish to add"""

    name = StepKeys.ADD_DAO_PROMPT_ID

    def __init__(self, cache):
        super().__init__()
        self.cache = cache

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What is the discord ID of the guild you'd like to add? "
            "(You can find this by right-clicking the guild icon and clicking "
            '"Copy ID")'
        )
        return sent_message, None


class AddDaoGetOrCreate(BaseStep):
    """This step checks if the supplied DAO ID already exists, and controls
    the flow accordingly to either create the DAO + user, or direct the
    user down the join flow."""

    name = StepKeys.ADD_DAO_GET_OR_CREATE

    def __init__(self, parent_thread, cache):
        self.parent_thread = parent_thread
        self.cache = cache

    async def send(self, message, user_id):
        message_content = message.content.strip()
        dao_id = None

        try:
            # we consider this exceptional if the supplied value is not
            # an actual number, but airtable will not accept values other
            # than strings for this column value
            dao_id = str(int(message_content))
        except ValueError:
            message = f"{message_content} is not a valid discord id!"
            raise ThreadTerminatingException()

        return None, {"guild_id": dao_id}

    async def control_hook(self, message, user_id):
        dao_id = str(int(message.content.strip()))
        self.parent_thread.guild_id = dao_id
        guild = await get_guild(dao_id)
        if guild:
            # Check if user is a member
            user = await fetch_user(user_id)
            guild_name = guild.get('name')

            if any(guild_user.get('guild_id') == guild.get('id') for guild_user in user.get('guild_users')):
                message = (
                    f"It looks like guild {dao_id} has already been added as "
                    f"{guild_name}, and it looks like you're already a member! "
                    " You can report your contributions with /report!"
                )
                raise ThreadTerminatingException(message)

            # guild exists, user does not, drop into /join flow
            await write_cache_metadata(user_id, self.cache, "guild_id", dao_id)
            await write_cache_metadata(user_id, self.cache, "guild_name", guild_name)
            return StepKeys.ADD_DAO_PREVIOUSLY_ADDED_PROMPT

        await create_guild(dao_id)

        # add validated dao_id to metadata cache for lookup on next step
        await write_cache_metadata(user_id, self.cache, "guild_id", dao_id)

        # Prompt for guild name
        return StepKeys.ADD_DAO_PROMPT_NAME


class AddDaoPromptName(BaseStep):
    """Prompts the user to input the name of the guild they wish to add"""

    name = StepKeys.ADD_DAO_PROMPT_NAME

    def __init__(self, cache):
        super().__init__()
        self.cache = cache

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What is the friendly name of the guild you'd like to add?"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        guild_name = message.content.strip()
        # retrieve dao_id from cache
        dao_id = await get_cache_metadata_key(user_id, self.cache, "guild_id")
        await update_guild_name(dao_id, guild_name)
        await write_cache_metadata(user_id, self.cache, "guild_name", guild_name)


class AddDaoPreviouslyAddedPrompt(BaseStep):
    """Prompts that a particular DAO has already been added"""

    name = StepKeys.ADD_DAO_PREVIOUSLY_ADDED_PROMPT
    trigger = True

    def __init__(self, cache):
        super().__init__()
        self.cache = cache


    async def send(self, message, user_id):
        guild_name = await get_cache_metadata_key(user_id, self.cache, "guild_name")
        guild_id = await get_cache_metadata_key(user_id, self.cache, "guild_id")

        return (
            await message.channel.send(
                f"It looks like guild {guild_id} has already been added as "
                f"{guild_name}, but you're not yet a member. Let's get that set up!"
            ),
            None
        )


class AddDaoSuccess(BaseStep):
    """Sends a success message for adding the Guild"""

    name = StepKeys.ADD_DAO_SUCCESS
    trigger = True

    def __init__(self, cache):
        super().__init__()
        self.cache = cache

    async def send(self, message, user_id):
        guild_name = await get_cache_metadata_key(user_id, self.cache, "guild_name")
        return (
            await message.channel.send(
                f"Thanks for adding {guild_name} as a new guild! Let's get "
                "you set up with a new profile for this guild. After setting it up, "
                "you can report your contributions using the /report command."
            ),
            None,
        )


class AddDaoJoinFlowOverride(BaseStep):
    """Overrides the Add_Dao flow and drops user into join flow"""

    name = StepKeys.ADD_DAO_JOIN

    def __init__(self, cache, parent_thread):
        super().__init__()
        self.cache = cache
        self.parent_thread = parent_thread

    # TODO: check reqs for join flow re: cache/populated fields
    async def send(self, message, user_id):
        guild_id = await get_cache_metadata_key(user_id, self.cache, "guild_id")
        return await set_thread_and_send(
            current_thread=self.parent_thread,
            next_thread_key=ThreadKeys.ONBOARDING.value,
            user_id=user_id,
            message=message,
            guild_id=guild_id)


class AddDao(BaseThread):
    name = ThreadKeys.ADD_DAO.value

    async def get_steps(self):
        dao_not_added_steps = (
            Step(current=AddDaoPromptName(self.cache))
            .add_next_step(AddDaoSuccess(self.cache))
            .add_next_step(AddDaoJoinFlowOverride(cache=self.cache, parent_thread=self))
        ).build()
        dao_previously_added_steps = (
            Step(current=AddDaoPreviouslyAddedPrompt(self.cache))
            .add_next_step(AddDaoJoinFlowOverride(cache=self.cache, parent_thread=self))
        ).build()
        steps = (
            Step(current=AddDaoPromptId(self.cache))
            .add_next_step(AddDaoGetOrCreate(self, self.cache))
            .fork([dao_not_added_steps, dao_previously_added_steps])
        )

        return steps.build()


from bot.common.threads.utils import (  # noqa: E402
    set_thread_and_send
)
