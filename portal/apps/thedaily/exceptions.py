from __future__ import unicode_literals
from builtins import str
class UpdateCrmEx(ValueError):
    def __init__(self, displaymessage=None):
        self.displaymessage = displaymessage

    def __str__(self):
        return "Unable to comunicate with CRM (%s)" % str(self.displaymessage)
