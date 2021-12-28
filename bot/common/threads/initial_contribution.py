# Contribution Flow
# 1. Ask if they would like to add their contributions
# Now that you have finished onboarding would you like to report your guild
# contributions in order to get rewarded
# 2a. If no responsd they can always start
# 2b. If they repond yes send them the the next contribution if they have already sent one# instructions
# 3. Ask them if they have completed the contribution
# 3a. No thank them
# 3b. yes send them a contgrats and link to report
# 4 Repeat if there is another contribution else send an indication of end
from common.threads.thread_builder import BaseThread, BaseStep
from common.threads.shared_steps import SelectGuildEmojiStep

from common.airtable import get_user_record, get_contribution_record, update_user


class SendContributionInstructions(BaseStep):
    """
    There is an assumption here that there will be
    at least one contribution.
    """

    name = StepKeys.SEND_CONTRIBUTION_INSTRUCTION

    def __init__(self, guild_id, contribution_number):
        self.guild_id = guild_id
        self.contribution_number = contribution_number

    # Get contributions
    # the build contribution instruction steps
    # create chains
    async def send(self, message, user_id):
        # next contribution
        # get contribution if none, fetch the first
        # if no first then say no initial contributions
        # Assumption the order of contribution flows cannot change
        # user_row = await get_user_record(user_id, self.guild_id)
        # user = user.get("fields")
        # # TODO: this isn't and actual number yet
        # contribution_number = user.get("next_contribution")
        channel = message.channel
        # if not contribution_number:
        #     contribution_number = 1
        # contribution = await get_contribution_record(
        #     user_id, self.guild_id, contribution_number
        # )
        # if not contribution:
        #     # there are no contributions terminate
        #     return None, None

        # # send intstruction return metadata
        # instructions = contribution.get("instructions")
        # embed = discord.Embed(colour=INFO_EMBED_COLOR, description=instructions title="Have you completed the below?")
        # sent_message = await channel.send(embed=embed)
        sent_message = await channel.send("hi")
        # # TODO: upate user contribution

        # await update_user(user.get("id"), "next_contribution", f"")

        return sent_message, None


# Handle yes and no scenario


class InitialContributionConfirmEmojiStep(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_CONFIRM_EMOJI.value
    emoji = True

    @property
    def emojis(self):
        return [YES_EMOJI, NO_EMOJI]

    async def handle_emoji(self, raw_reaction):
        if raw_reaction.emoji.name in self.emojis:
            if raw_reaction.emoji.name == NO_EMOJI:
                return StepKeys.INITIAL_CONTRIBUTION_REJECT.value, None
            return StepKeys.INITIAL_CONTRIBUTION_ACCEPT.value, None
        raise Exception("Reacted with the wrong emoji")

    async def save(self, message, guild_id, user_id):
        # TODO: Save to the contribution to the users base
        pass


# Then two paths and repeat
class InitialContributionAccept(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_ACCEPT

    async def send(self, message, userid):
        channel = message.channel
        await channel.send(
            "Congratulations on competeting that contribution and improving our community!"
        )

    # This should point to the next step


class InitialContributionReject(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_REJECT

    async def send(self, message, userid):
        channel = message.channel
        await channel.send(
            "No worries! When you do complete that contribution run the `/add_initial_contribution command!`"
        )

class InitialContributionReportCommand(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_REPORT_COMMAND

    async def send(self, message, userid):
        channel = message.channel
        await channel.send(""Test)



class InitialContributions(BaseThread):

    # Get contributions
    # build chain
    def build_steps():
        # Get initial contributions
        # find which contribution the user is at
        # start at the next step
        # if the user has completed all the steps then
        # send an error
        # there should be a check at the command level preventing that path
        contribution_records = await get_contribution_record(
            self.user_id, self.guild_id
        )
        last_step = None
        for record in sorted(
            contribution_records,
            key=lambda record: record.get("fields", {"order": 1}).get("order"),
        ):
            fields = record.get("fields")
            order = fields.get("order")
            # On initial pass make sure to add report step
            yes_fork = InitialContributionAccept()
            if last_step:
                yes_fork.add_next_step(last_step)
            fork_steps = [yes_fork, InitialContributionReject]
            last_step = (
                Step(
                    current=SendContributionInstructions(
                        guild_id=self.guild_id, contribution_number=order
                    )
                )
                .add_next_step(InitialContributionConfirmEmojiStep())
                .fork(fork_steps)
                .build()
            )
        if not last_step:
            raise Exception(
                "Steps are None, most likely no contribution records were found"
            )
        return last_step.

    @property
    def steps(self):
        steps = Step(current=SelectGuildEmojiStep(cls=self)).add_next_step(
            self.build_steps()
        )
        return steps.build()
