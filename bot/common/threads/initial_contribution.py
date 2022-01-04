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
import discord
import hashlib
from common.airtable import (
    add_user_to_contribution,
    get_highest_contribution_records,
    get_contribution_records,
    find_user,
    get_user_record,
)
from common.threads.thread_builder import (
    BaseThread,
    BaseStep,
    StepKeys,
    Step,
    ThreadKeys,
)
from common.threads.shared_steps import SelectGuildEmojiStep
from config import YES_EMOJI, NO_EMOJI, INFO_EMBED_COLOR


class SendContributionInstructions(BaseStep):
    """
    There is an assumption here that there will be
    at least one contribution.
    """

    name = StepKeys.SEND_CONTRIBUTION_INSTRUCTION.value

    def __init__(self, guild_id, contribution_number, instruction, total_contributions):
        self.guild_id = guild_id
        self.contribution_number = contribution_number
        self.instruction = instruction
        self.total_contributions = total_contributions
        self.no_record = False

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
        # # send intstruction return metadata

        # TODO if user completed respond completed
        # and terinate with end
        # I am going to do this temporarily
        user_record = await get_user_record(user_id, self.guild_id)
        user_record_id = user_record.get("fields").get("guild_id")

        record = await get_highest_contribution_records(
            self.guild_id, user_record_id, self.total_contributions
        )
        if record:
            embed = discord.Embed(
                colour=INFO_EMBED_COLOR,
                description="You have already completed all of the initial contributions for this guild!"
                " To report new contributions use the `/report` command",
            )
            sent_message = await channel.send(embed=embed)
            self.no_record = True
            return message, None

        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description=self.instruction,
            title="Have you completed the below?",
        )
        sent_message = await channel.send(embed=embed)
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)
        # # TODO: upate user contribution

        await add_user_to_contribution(self.guild_id, user_id, self.contribution_number)

        return sent_message, None

    async def control_hook(self, message, user_id):
        if self.no_record:
            return StepKeys.END.value


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
    name = StepKeys.INITIAL_CONTRIBUTION_ACCEPT.value
    trigger = True

    async def send(self, message, userid):
        channel = message.channel
        message = await channel.send(
            "Congratulations on competeting that contribution and improving our community!"
        )
        return message, None

    # This should point to the next step


class InitialContributionReject(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_REJECT.value

    async def send(self, message, userid):
        channel = message.channel
        message = await channel.send(
            "No worries! When you do complete that contribution run the `/add_initial_contribution command!`"
        )
        return message, None


class InitialContributionReportCommand(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_REPORT_COMMAND.value

    def __init__(self, cls):
        self.cls = cls

    async def send(self, message, userid):
        channel = message.channel
        message = await channel.send(
            "In order to send add more new contributions call the `/report` command"
        )
        return message, None


class InitialContributions(BaseThread):
    name = ThreadKeys.INITIAL_CONTRIBUTIONS.value

    # Get contributions
    # build chain
    async def build_steps(self):
        # Get initial contributions
        # find which contribution the user is at
        # start at the next step
        # if the user has completed all the steps then
        # send an error
        # there should be a check at the command level preventing that path

        if not self.guild_id:
            raise Exception("No provided guild_id for Initial COntribution thread")
        print("Guild id")
        contribution_records = await get_contribution_records(self.guild_id)
        previous_step = None
        for i, record in enumerate(
            sorted(
                contribution_records,
                key=lambda record: record.get("fields", {"order": 1}).get("order"),
            )
        ):
            print(len(contribution_records))
            fields = record.get("fields")
            order = fields.get("order")
            instructions = fields.get("instructions")

            current_step = Step(
                current=SendContributionInstructions(
                    guild_id=self.guild_id,
                    contribution_number=order,
                    instruction=instructions,
                    total_contributions=len(contribution_records),
                ),
                hash_=hashlib.sha256(
                    f"{previous_step.hash_}{SendContributionInstructions.name}".encode()
                ).hexdigest()
                if previous_step
                else hashlib.sha256("".encode()).hexdigest(),
            )

            # On initial pass make sure to add report step
            yes_fork = Step(current=InitialContributionAccept())
            print(len(contribution_records), i)
            if len(contribution_records) == i + 1:
                print("ADDED REPORT")
                yes_fork.add_next_step(InitialContributionReportCommand(cls=self))
            fork_steps = [
                yes_fork,
                Step(current=InitialContributionReject()).build(),
            ]
            print("Root")
            print(hashlib.sha256("".encode()).hexdigest())
            print(
                hashlib.sha256(
                    f"{previous_step.hash_}{SendContributionInstructions.name}".encode()
                ).hexdigest()
                if previous_step
                else hashlib.sha256("".encode()).hexdigest()
            )
            current_tree = (
                current_step.add_next_step(InitialContributionConfirmEmojiStep())
                .fork(fork_steps)
                .build()
            )

            if not previous_step:
                previous_step = current_tree
                previous_step = yes_fork
            else:
                # Return the yes path
                previous_step.add_next_step(current_tree)
                print(current_tree.next_steps.keys())
                print(
                    current_tree.next_steps.get(
                        StepKeys.INITIAL_CONTRIBUTION_ACCEPT.value
                    )
                )
                previous_step = yes_fork
            print(previous_step.hash_)
        if not previous_step:
            raise Exception(
                "Steps are None, most likely no contribution records were found"
            )
        return previous_step.build()

    async def get_steps(self):
        contribution_step = await self.build_steps()
        return contribution_step.build()
