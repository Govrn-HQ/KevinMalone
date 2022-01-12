import pytest
import hashlib

from common.threads.thread_builder import BaseThread, Step, BaseStep


class EmojiLogic(BaseStep):
    emoji = True

    async def handle_emoji(self, raw_reaction):
        pass


class RedLogic(BaseStep):
    name = "red"

    async def send(self, message, user_id):
        pass


class BlueLogic(BaseStep):
    name = "blue"

    async def send(self, message, user_id):
        pass


class LeftLogic(BaseStep):
    name = "left"

    async def send(self, message, user_id):
        pass


class RightLogic(BaseStep):
    name = "right"

    async def send(self, message, user_id):
        pass


class MockLogic(BaseStep):
    name = "mock_logic"

    async def send(self, message, user_id):
        pass


class SingleThread(BaseThread):
    async def get_steps(self):
        return Step(current=MockLogic())


class MultiThread(BaseThread):
    async def get_steps(self):
        return (
            Step(current=MockLogic())
            .add_next_step(MockLogic())
            .add_next_step(MockLogic())
            .build()
        )


class SingleForkThread(BaseThread):
    async def get_steps(self):
        left = LeftLogic()
        right = RightLogic()
        return (
            Step(current=MockLogic())
            .add_next_step(MockLogic())
            .fork([left, right])
            .build()
        )


class MultiForkThread(BaseThread):
    async def get_steps(self):
        red = RedLogic()
        blue = BlueLogic()

        left = Step(current=LeftLogic()).fork([red, blue]).build()
        right = Step(current=RightLogic()).add_next_step(left).build()
        return (
            Step(current=MockLogic())
            .add_next_step(MockLogic())
            .fork([left, right])
            .build()
        )


class EmojiThread(BaseThread):
    async def get_steps(self):
        return Step(current=EmojiLogic)


def get_root_hash():
    return hashlib.sha256("".encode()).hexdigest()


### Test find step ###


@pytest.mark.asyncio
async def test_find_single_step():
    """
    Find a step in a thread with a single step
    """
    root_hash = get_root_hash()

    steps = await SingleThread(
        user_id="", current_step=root_hash, message_id="", guild_id=""
    ).get_steps()
    step = SingleThread.find_step(steps, root_hash)
    assert step.hash_ == root_hash


@pytest.mark.asyncio
async def test_find_mulitple_step_no_forks():
    """
    Find a step in a thread with no forks and multiple steps
    """
    root_hash = get_root_hash()

    steps = await MultiThread(
        user_id="", current_step=root_hash, message_id="", guild_id=""
    ).get_steps()
    third_step = steps.get_next_step(MockLogic.name).get_next_step(MockLogic.name)
    step = SingleThread.find_step(steps, third_step.hash_)
    assert step.hash_ == third_step.hash_


@pytest.mark.asyncio
async def test_find_mulitple_step_single_fork():
    """
    Find a step in a thread with with a single fork
    """
    root_hash = get_root_hash()

    steps = await SingleForkThread(
        user_id="", current_step=root_hash, message_id="", guild_id=""
    ).get_steps()
    right_step = steps.get_next_step(MockLogic.name).get_next_step(RightLogic.name)
    step = SingleForkThread.find_step(steps, right_step.hash_)
    assert step.hash_ == right_step.hash_


@pytest.mark.asyncio
async def test_find_mulitple_step_multiple_fork():
    """
    Find a step in a thread with multiple forks
    """
    root_hash = get_root_hash()

    steps = await MultiForkThread(
        user_id="", current_step=root_hash, message_id="", guild_id=""
    ).get_steps()
    blue_step = (
        steps.get_next_step(MockLogic.name)
        .get_next_step(RightLogic.name)
        .get_next_step(LeftLogic.name)
        .get_next_step(BlueLogic.name)
    )
    step = MultiForkThread.find_step(steps, blue_step.hash_)
    assert step.hash_ == blue_step.hash_


# Test Thread __await__ #


@pytest.mark.asyncio
async def test_thread_steps():
    root_hash = get_root_hash()

    thread = await MultiForkThread(
        user_id="", current_step=root_hash, message_id="", guild_id=""
    )
    assert thread.steps


@pytest.mark.asyncio
async def test_thread_steps():
    root_hash = get_root_hash()

    thread = await MultiForkThread(
        user_id="", current_step=root_hash, message_id="", guild_id=""
    )
    assert thread.steps


@pytest.mark.asyncio
async def test_thread_steps():
    root_hash = get_root_hash()

    thread = MultiForkThread(
        user_id="", current_step=root_hash, message_id="", guild_id=""
    )
    with pytest.raises(Exception):
        thread.send()


# Test thread send #


@pytest.mark.asyncio
async def test_thread_send_emoji_step():
    """
    Throw an error if we try to send on an emoji step
    """
    root_hash = get_root_hash()
    thread = EmojiThread(user_id="", current_step=root_hash, message_id="", guild_id="")
    with pytest.raises(Exception):
        await thread.send()


# @pytest.mark.asyncio
# async def test_thread_send_emoji_step():
#     """
#     Throw an error if we try to send on an emoji step
#     """
#     root_hash = get_root_hash()
#     thread = EmojiThread(user_id="", current_step=root_hash, message_id="", guild_id="")
#     with pytest.raises(Exception):
#         await thread.send()


# send
# 2. If there was a previous step and not skipped then save
# 3. if there was a previous step and it was skipped then don't save
# 4. if there wasn't a previous step then don't save
# 5. if metadata from send then get thread and add metadata
# 6. if not metadata skip
# 7. if not next step then delete key
# 8. if overriden with end delete key
# 9. if override step then call send again with that step
# 10. if trigger is set then run the next step,
# 11. if triggered then and next step is an emoji throw the appropriate error
# 12. test cache is set at the end
