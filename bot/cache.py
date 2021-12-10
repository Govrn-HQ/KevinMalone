import json
import logging

from airtable import find_user, update_user
from enum import Enum
from config import Redis, YES_EMOJI, NO_EMOJI
from typing import Dict, Optional

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def build_cache_value(thread_name, step, guild_id, message_id=""):
    return json.dumps(
        {
            "thread": thread_name,
            "step": step,
            "guild_id": guild_id,
            "message_id": message_id,
        }
    )


# enums for thread keys
# enum for step keys
class ThreadKeys(Enum):
    ONBOARDING = "onboarding"


class StepKeys(Enum):
    USER_DISPLAY_CONFIRM = "user_display_confirm"
    USER_DISPLAY_CONFIRM_EMOJI = "user_display_confirm_emoji"
    USER_DISPLAY_SUBMIT = "user_display_submit"
    ADD_USER_TWITTER = "add_user_twitter"


class BaseThread:
    pass


class BaseStep:
    emoji = False

    async def save(self, message):
        pass


class UserDisplayConfirmationStep(BaseStep):
    name = StepKeys.USER_DISPLAY_CONFIRM.value
    msg = "Would you like your govern display name to be"

    @property
    def emojis():
        return [YES_EMOJI, NO_EMOJI]

    async def send(self, message, user_id):
        from commands import bot

        user = await bot.fetch_user(user_id)
        channel = message.channel
        sent_message = await channel.send(f"{self.msg} `{user.display_name}`")
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)
        return sent_message


# save is a single branch so it can be one to one
# handle_emoji can branch and the airtable logic can handle that
class UserDisplayConfirmationEmojiStep(BaseStep):
    name = StepKeys.USER_DISPLAY_CONFIRM_EMOJI.value
    emoji = True

    @property
    def emojis():
        return [YES_EMOJI, NO_EMOJI]

    async def handle_emoji(self, reaction):
        if reaction.emoji in self.emojis:
            if reaction.emoji == NO_EMOJI:
                return StepKeys.USER_DISPLAY_SUBMIT.value
            return StepKeys.ADD_USER_TWITTER.value
        raise Exception("Reacted with the wrong emoji")

    """
    This is where I left off
    TODO: Add guild id to redis value
    then I can upate the appropriate record in
    Discord
    """

    async def save(self, message, guild_id):
        record_id = await find_user(message.author.id, guild_id)
        await update_user(record_id, "display_name", message.author.name)


class UserDisplaySubmitStep(BaseStep):
    name = StepKeys.USER_DISPLAY_SUBMIT.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(f"Updated display name to {message.content}")
        return sent_message


class AddUserTwitterStep(BaseStep):
    name = StepKeys.ADD_USER_TWITTER.value

    async def send(self):
        pass

    async def save(self, message):
        pass


@dataclass
class Step:
    current: BaseStep
    next_steps: Optional[Dict[str, BaseStep]] = field(default_factory=dict)
    previous_step: Optional[BaseStep] = field(default=None)

    def add_next_step(self, step):
        step.previous_step = self.current
        self.next_steps[step.current.name] = step
        return self

    def get_next_step(self, key):
        step = self.next_steps.get(key, "")
        if step == "":
            raise Exception(
                f"Not a valid next step! current {self.current.name} and next: {key}"
            )
        return step


# from message
# check user
# if user has key
# Pass into function that parses and picks the appropriate class
# This class will take the users input and then, store and respond
# Each thread should have a step parser that picks the appropriate step
# And each step should point to the next step
class Onboarding(BaseThread):
    name = ThreadKeys.ONBOARDING.value

    def __init__(self, user_id, current_step, message_id, guild_id):
        # Check here that get is not null
        if not current_step:
            raise Exception(f"No step for {current_step}")
        self.step = self.find_step(self.steps, current_step)
        self.user_id = user_id
        self.message_id = message_id
        self.guild_id = guild_id

    @property
    def steps(self):
        data_retrival_chain = Step(current=AddUserTwitterStep())
        user_display_accept = Step(current=UserDisplaySubmitStep()).add_next_step(
            data_retrival_chain
        )
        user_display_confirm_emoji = (
            Step(current=UserDisplayConfirmationEmojiStep())
            .add_next_step(user_display_accept)
            .add_next_step(data_retrival_chain)
        )
        steps = Step(current=UserDisplayConfirmationStep()).add_next_step(
            user_display_confirm_emoji
        )
        return steps

    def find_step(self, steps, name):
        print("Steps")
        print(steps)
        print(name)
        if steps.current.name == name:
            return steps
        for step in steps.next_steps:
            steps = self.find_step(step, name)
            if steps:
                return steps
        return None

    async def send(self, message):
        logger.info(f"Send {self.step}")
        if self.step.current.emoji is True:
            await message.channel.send(
                "Please react with one of the above emojis to continue!"
            )
            return
        if self.step.previous_step:
            self.previous_step.save(message)
        msg = await self.step.current.send(message, self.user_id)

        if not self.step.next_steps:
            return await Redis.delete(self.user_id)
        return await Redis.set(
            self.user_id,
            build_cache_value(
                self.name,
                list(self.step.next_steps.values())[0].current.name,
                self.guild_id,
                msg.id,
            ),
        )

    # Emoji cannot follow emoji
    async def handle_reaction(self, reaction):
        logger.info(f"Emoji {reaction}")
        try:
            step_name = await self.step.current.handle_emoji(reaction)
        except Exception:
            await reaction.message.channel.send(
                f"In order to move to the following step please react with one of {self.step.current.emojis}"
            )
            return

        next_step = self.step.current.get_next_step(step_name)
        if not next_step:
            return await Redis.delete(self.user_id)
        self.step = next_step
        await self.send(reaction.message)


def get_thread(user_id, key):
    val = json.loads(key)
    thread = val.get("thread")
    step = val.get("step")
    message_id = val.get("message_id")
    guild_id = val.get("guild_id")
    if thread == ThreadKeys.ONBOARDING.value:
        return Onboarding(user_id, step, message_id, guild_id)
    raise Exception("Unknown Thread!")
