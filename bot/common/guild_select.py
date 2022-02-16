import json
import hashlib
from bot.common.threads.thread_builder import (
    BaseThread,
    ThreadKeys,
    Step,
    BaseStep,
    StepKeys,
    build_cache_value,
)
from bot.common.threads.shared_steps import SelectGuildEmojiStep

from bot.common.threads.onboarding import Onboarding  # noqa: E402
from bot.common.threads.update import UpdateProfile  # noqa: E402
from bot.common.threads.initial_contribution import InitialContributions
from bot.common.threads.report import Report
from bot.common.threads.points import Points
from bot.config import Redis


async def get_thread(user_id, key):
    val = json.loads(key)
    thread = val.get("thread")
    step = val.get("step")
    message_id = val.get("message_id")
    guild_id = val.get("guild_id")
    if thread == ThreadKeys.ONBOARDING.value:
        return await Onboarding(user_id, step, message_id, guild_id)
    elif thread == ThreadKeys.UPDATE_PROFILE.value:
        return await UpdateProfile(user_id, step, message_id, guild_id)
    elif thread == ThreadKeys.INITIAL_CONTRIBUTIONS.value:
        return await InitialContributions(user_id, step, message_id, guild_id)
    elif thread == ThreadKeys.GUILD_SELECT.value:
        return await GuildSelect(user_id, step, message_id, guild_id)
    elif thread == ThreadKeys.REPORT.value:
        return await Report(user_id, step, message_id, guild_id)
    elif thread == ThreadKeys.POINTS.value:
        return await Points(user_id, step, message_id, guild_id)
    raise Exception("Unknown Thread!")


class OverrideThreadStep(BaseStep):
    """A step that overwrites the current thread

    This step gets the name of the jump thread from
    the cache metadata and then overwrites the current
    steps in memory with the new threads steps.

    """

    name = StepKeys.OVERRIDE_THREAD.value

    def __init__(self, cls):
        self.cls = cls

    async def send(self, message, user_id):
        thread = await get_thread(
            user_id,
            build_cache_value(
                self.cls.command_name,
                hashlib.sha256("".encode()).hexdigest(),
                self.cls.guild_id,
                message.id,
            ),
        )
        # this is dangerous
        self.cls.get_steps = thread.get_steps
        self.cls.step = thread.step
        self.cls.name = thread.name
        message, metadata = await thread.step.current.send(message, user_id)

        return message, metadata


class GuildSelect(BaseThread):
    """A thread that sets the guild_id for another thread

    This thread is typically called from a command which
    will set the next thread to jump to on the next step
    and responds with an emoji prompt for a user to set
    guild_id.
    """

    name = ThreadKeys.GUILD_SELECT.value

    def __await__(self):
        async def init(self):
            await self._init_steps()
            key_vals = await Redis.get(self.user_id)
            if key_vals:
                self.command_name = (
                    json.loads(key_vals).get("metadata").get("thread_name")
                )
            return self

        return init(self).__await__()

    async def get_steps(self):
        steps = Step(current=SelectGuildEmojiStep(cls=self)).add_next_step(
            OverrideThreadStep(self)
        )
        return steps.build()
