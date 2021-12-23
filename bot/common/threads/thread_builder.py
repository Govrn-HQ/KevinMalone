import copy
import json
import hashlib
import logging

from common.core import bot
from enum import Enum
from config import Redis
from typing import Dict, Optional

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def build_cache_value(thread, step, guild_id, message_id="", **kwargs):
    return json.dumps(
        {
            "thread": thread,
            "step": step,
            "guild_id": guild_id,
            "message_id": message_id,
            **kwargs,
        }
    )


class ThreadKeys(Enum):
    ONBOARDING = "onboarding"
    UPDATE_PROFILE = "update_profile"


class StepKeys(Enum):
    USER_DISPLAY_CONFIRM = "user_display_confirm"
    USER_DISPLAY_CONFIRM_EMOJI = "user_display_confirm_emoji"
    USER_DISPLAY_SUBMIT = "user_display_submit"
    ADD_USER_TWITTER = "add_user_twitter"
    ONBOARDING_CONGRATS = "onboarding_congrats"
    ADD_USER_WALLET_ADDRESS = "add_user_wallet_address"
    ADD_USER_DISCOURSE = "add_user_discourse"
    SELECT_GUILD_EMOJI = "select_guild_emoji"
    USER_UPDATE_FIELD_SELECT = "user_update_select"
    UPDATE_PROFILE_FIELD_EMOJI = "update_profile_field_emoji"
    UPDATE_FIELD = "update_field"
    CONGRATS_UPDATE_FIELD = "congrats_update_field"
    DISPLAY_NAME_REQUEST = "display_name_request"
    GOVRN_PROFILE_PROMPT = "govrn_profile_prompt"
    GOVRN_PROFILE_PROMPT_EMOJI = "govrn_profile_prompt_emoji"
    GOVRN_PROFILE_PROMPT_REJECT = "govrn_profile_prompt_reject"
    GOVRN_PROFILE_PROMPT_ACCEPT = "govrn_profile_prompt_accept"
    GOVRN_PROFILE_PROMPT_ACCEPT_EMOJI = "govrn_profile_prompt_accept_emoji"
    GOVRN_PROFILE_REUSE = "govrn_profile_reuse"
    END = "end"


class BaseThread:
    def __init__(self, user_id, current_step, message_id, guild_id):
        if not current_step:
            raise Exception(f"No step for {current_step}")
        self.user_id = user_id
        self.message_id = message_id
        self.guild_id = guild_id
        self.step = self.find_step(self.steps, current_step)
        self.skip = False

    def find_step(self, steps, hash_):
        if steps.hash_ == hash_:
            return steps
        for _, step in steps.next_steps.items():
            steps = self.find_step(step, hash_)
            if steps:
                return steps
        return None

    async def send(self, message):
        logger.info(f"Send {self.step.hash_}")
        if self.step.current.emoji is True:
            await message.channel.send(
                "Please react with one of the above emojis to continue!"
            )
            return
        if (
            self.step.previous_step
            and self.step.previous_step.current
            and not self.skip
        ):
            await self.step.previous_step.current.save(
                message, self.guild_id, self.user_id
            )
        msg, metadata = await self.step.current.send(message, self.user_id)
        if not metadata:
            u = await Redis.get(self.user_id)
            if u:
                metadata = json.loads(u).get("metadata")
        # automation hook
        # if returns a step
        # override linear step
        if not self.step.next_steps:
            return await Redis.delete(self.user_id)
        step = list(self.step.next_steps.values())[0]
        override_step = await self.step.current.control_hook(message, self.user_id)
        if override_step == StepKeys.END.value:
            return await Redis.delete(self.user_id)
        if override_step:
            step = self.step.get_next_step(override_step)
            # TODO: I am guessing this metadata will need to be refactored
            self.step = step
            return await self.send(message)
            # as it does not take into account the previous metadata

        return await Redis.set(
            self.user_id,
            build_cache_value(
                self.name,
                step.hash_,
                self.guild_id,
                msg.id,
                metadata=metadata,
            ),
        )

    # TODO: assumption Emoji cannot follow emoji, message must follow emoji
    async def handle_reaction(self, reaction, user):

        logger.info(f"Emoji {reaction}")
        # TODO: Add some error handling
        channel = await bot.fetch_channel(reaction.channel_id)
        message = await channel.fetch_message(reaction.message_id)

        if reaction.message_id != self.message_id:
            await channel.send(
                "Emoji reaction on the wrong message., "
                "Please react to your most recent message"
            )
            return
        try:
            step_name, skip = await self.step.current.handle_emoji(reaction)
        except Exception:
            logger.exception("Fiailed to handle the emoji")
            await channel.send(
                "In order to move to the following step please "
                "react with one of the already existing emojis"
            )
            return
        if skip is True:
            next_step = self.step
        else:
            if not step_name:
                if not list(self.step.next_steps.values()):
                    return await Redis.delete(self.user_id)
                step_name = list(self.step.next_steps.values())[0].current.name
            next_step = self.step.get_next_step(step_name)
        if not next_step:
            return await Redis.delete(self.user_id)
        self.step = next_step
        self.skip = skip
        await self.send(message)


class BaseStep:
    emoji = False

    async def save(self, message, guild_id, user_id):
        pass

    async def control_hook(self, message, user_id):
        pass


# TODO: There is an issue here if the same class is used on a branch
# Make sure that at a the a fork can use a previous branch
@dataclass
class Step:
    current: BaseStep
    next_steps: Optional[Dict[str, BaseStep]] = field(default_factory=dict)
    previous_step: Optional[BaseStep] = field(default=None)
    hash_: str = hashlib.sha256("".encode()).hexdigest()

    def add_next_step(self, step):
        if isinstance(step, BaseStep):
            step = Step(current=step)
        step.previous_step = self
        step.hash_ = hashlib.sha256(
            f"{self.hash_}{step.current.name}".encode()
        ).hexdigest()
        self.next_steps[step.current.name] = step
        return step

    def fork(self, logic_steps):
        if not logic_steps:
            Exception("No steps specified")
        for step in logic_steps:
            if isinstance(step, BaseStep):
                step = Step(current=step)
            step.previous_step = self
            step.hash_ = hashlib.sha256(
                f"{self.hash_}{step.current.name}".encode()
            ).hexdigest()

            self.next_steps[step.current.name] = self._copy_children(step)

        return self

    def _copy_children(self, step):
        next_steps = {}
        for k, s in step.next_steps.items():
            c = copy.copy(s)
            next_steps[k] = self._copy_children(c)
        step.next_steps = next_steps
        return copy.copy(step)

    def build(self):
        previous = self.previous_step
        while previous:
            if not previous.previous_step:
                break
            previous = previous.previous_step
        if previous is None:
            return self
        return previous

    def get_next_step(self, key):
        step = self.next_steps.get(key, "")
        if step == "":
            raise Exception(
                f"Not a valid next step! current {self.current.name} and next: {key}"
                f" Valid nex steps: {list(self.next_steps.keys())}"
            )
        return step
