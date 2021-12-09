from enum import Enum

# enums for thread keys
# enum for step keys
class ThreadKeys(Enum):
    ONBOARDING = "onboarding"


class StepKeys(Enum):
    USER_DISPLAY_CONFIRM = "user_display_confirm"
    ADD_USER_TWITTER = "add_user_twitter"


# from message
# check user
# if user has key
# Pass into function that parses and picks the appropriate class
# This class will take the users input and then, store and respond
# Each thread should have a step parser that picks the appropriate step
# And each step should point to the next step
