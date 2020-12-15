from django.db.models import ForeignKey
from django.db.models import SubfieldBase
from core.middleware import threadlocals
#TODO chequear si se puede borrar, se usaba para poner automaticamente el usuario que estaba modificando un Evento o un Articulo
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
