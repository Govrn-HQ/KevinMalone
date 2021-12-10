from enum import Enum
from config import Redis, YES_EMOJI, NO_EMOJI
from typing import Dict, Optional

from dataclasses import dataclass


def build_cache_value(thread_name, step, message_id=""):
    return f"{thread_name}___{step}___{message_id}"


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

    async def send(self, message):
        channel = message.channel
        sent_message = await channel.send(f"{self.msg} {message.author}")
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)
        return sent_message

    """
    This is where I left off
    TODO: Add guild id to redis value
    then I can upate the appropriate record in
    Discord
    """
    async def save(self, message):
        record_id = find_user(message.author.id, message.)
        await 


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
            return
        raise Exception("Reacted with the wrong emoji")


class UserDisplaySubmitStep(BaseStep):
    name = StepKeys.USER_DISPLAY_SUBMIT.value

    async def send(self, message):
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
    next_steps: Optional[Dict[str, BaseStep]] = None
    previous_step = Optional[BaseStep] = None

    def add_next_step(self, step):
        step.previous_step = self.current
        self.next_steps[step.current.name] = step

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

    def __init__(self, user_id, current_step, message_id):
        # Check here that get is not null
        self.step = self.steps.get(current_step,)
        self.user_id = user_id
        self.message_id = message_id

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
        return Step(current=UserDisplayConfirmationStep()).add_next_step(
            user_display_confirm_emoji
        )

    async def send(self, message):
        if self.step.current.emoji is True:
            await message.channel.send(
                "Please react with one of the above emojis to continue!"
            )
            return
        if self.step.previous_step:
            self.previous_step.save(message)
        msg = await self.step.current.send(message)

        if not self.step.next_step:
            return Redis.delete(self.user_id)
        return Redis.set(
            self.user_id, build_cache_value(self.name, self.step.next_step.name, msg.id)
        )

    # Emoji cannot follow emoji
    async def handle_reaction(self, reaction):
        try:
            step_name = await self.step.current.handle_emoji(reaction)
        except Exception:
            await reaction.message.channel.send(
                f"In order to move to the following step please react with one of {self.step.current.emojis}"
            )
            return

        next_step = self.step.current.get_next_step(step_name)
        if not next_step:
            return Redis.delete(self.user_id)
        self.step = next_step
        await self.send(reacion.message)


def get_thread(user_id, key):
    thread, step, message_id = key.split("___")
    if thread == ThreadKeys.ONBOARDING.value:
        return Onboarding(user_id, step, message_id)
    raise Exception("Unknown Thread!")
