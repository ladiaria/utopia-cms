
from builtins import str

from django.forms import ValidationError


class UpdateCrmEx(ValueError):
    def __init__(self, displaymessage=None):
        self.displaymessage = displaymessage

    def __str__(self):
        return "Unable to comunicate with CRM (%s)" % str(self.displaymessage)


class EmailValidationError(ValidationError):
    INVALID = "invalid"
