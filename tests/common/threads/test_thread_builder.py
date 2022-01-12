import pytest
import hashlib

from common.threads.thread_builder import BaseThread, Step, BaseStep


class MockLogic(BaseStep):
    name = "mock_logic"

    async def send(self, message, user_id):
        pass


class SingleStep(BaseThread):
    async def get_steps(self):
        return Step(current=MockLogic)


@pytest.mark.asyncio
async def test_find_single_step():
    root_hash = hashlib.sha256("".encode).hexdigest

    steps = await SingleStep().get_steps(root_hash)
    step = SingleStep.find_step(steps, root_hash)
    assert step.hash_ == root_hash


# Tests
# 1. find step single step
# 2. find step in a line of steps
# 3. find step with a fork
# 4. find step with multiple forks

# __await__
# 1. test steps are fetched and set
# 2. test error is thrown if not awaited
# 3.

# send
# 1. If emoji step throw an error
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
