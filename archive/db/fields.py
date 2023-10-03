# deprecated, archived. Used time ago to set the user who was changing models
from __future__ import unicode_literals

from django.db.models import ForeignKey

from core.middleware import threadlocals


class AuthUserForeignKey(ForeignKey):
    ''' autosave auth user '''

    def __init__(self, *args, **kwargs):
        super(AuthUserForeignKey, self).__init__(*args, **kwargs)

    def get_db_prep_save(self, value):
        user = threadlocals.get_current_user()
        if user != None and self.editable == True or value == None:
            return user.id
        elif value != None:
            return value
        else:
            return None
