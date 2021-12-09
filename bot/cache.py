from enum import Enum
from config import Redis
from typing import Optional

from dataclasses import dataclass


def build_cache_value(thread_name, step):
    return f"{thread_name}___{step}"


# enums for thread keys
# enum for step keys
class ThreadKeys(Enum):
    ONBOARDING = "onboarding"


class StepKeys(Enum):
    USER_DISPLAY_CONFIRM = "user_display_confirm"
    ADD_USER_TWITTER = "add_user_twitter"


class BaseThread:
    pass


class BaseStep:
    pass


class UserDisplayConfirmationStep(BaseStep):
    name = StepKeys.USER_DISPLAY_CONFIRM.value

    async def send(self):
        pass


class AddUserTwitterStep(BaseStep):
    name = StepKeys.ADD_USER_TWITTER.value

    async def send(self):
        pass


@dataclass
class Step:
    current: BaseStep
    next_step: Optional[BaseStep]


# from message
# check user
# if user has key
# Pass into function that parses and picks the appropriate class
# This class will take the users input and then, store and respond
# Each thread should have a step parser that picks the appropriate step
# And each step should point to the next step
class Onboarding(BaseThread):
    name = ThreadKeys.ONBOARDING.value

    def __init__(self, user_id, current_step):
        # Check here that get is not null
        self.step = self.steps.get(
            current_step,
            Step(
                current=UserDisplayConfirmationStep(), next_step=AddUserTwitterStep(),
            ),
        )
        self.user_id = user_id

    @property
    def steps(self):
        return {
            StepKeys.USER_DISPLAY_CONFIRM.value: Step(
                current=UserDisplayConfirmationStep(), next_step=AddUserTwitterStep(),
            ),
            StepKeys.ADD_USER_TWITTER.value: Step(
                current=AddUserTwitterStep(), next_step=None,
            ),
        }

    async def send(self):
        await self.step.current.send()
        if not self.step.next_step:
            return Redis.delete(self.user_id)
        return Redis.set(
            self.user_id, build_cache_value(self.name, self.step.next_step.name)
        )


def get_thread(user_id, key):
    thread, step = key.split("___")
    if thread == ThreadKeys.ONBOARDING.value:
        return Onboarding(user_id, step)
    raise Exception("Unknown Thread!")
