# -*- coding: utf-8 -*-

"""
Test cases:
* 1 subscriber, 1 user                                 OK
* 2 subscribers, 2 users                               OK
* 2 subscribers, 1 user                                OK
* 2 subscribers, no email for the user at the end
* 2 subscribers, 2 users (one with things)

This command should be reviewed and updated/deleted, apacheco

"""
from collections import Iterable

from django.core.management.base import BaseCommand
from django.core.exceptions import MultipleObjectsReturned
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Count
from django.template.loader import render_to_string
from django.contrib.auth.hashers import is_password_usable
from django.contrib.admin.util import NestedObjects

from core.models import Article
from thedaily.models import Subscriber

# Classes that cannot be deleted in a user or subscriber cascade deletion
PROTECTED_CLASSES = (Article, )


def delete_bastard(obj):
    """
    Delete the bastard obj, user or subscriber.
    Don't delete if cascade will delete a protected object, in this case alert.
    """
    collector = NestedObjects(using=DEFAULT_DB_ALIAS)
    collector.collect([obj])

    def candelete(item):
        if isinstance(item, Iterable):
            return all([candelete(i) for i in item])
        elif type(item) in PROTECTED_CLASSES:
            print("%s not deleted because has %s" % (obj, item))
            return False
        else:
            return True

    if candelete(collector.nested()):
        print("Deleting %s and %s" % (obj, collector.nested()))
        obj.delete()


class Command(BaseCommand):
    help = 'Merge subscribers and users with same document'
    args = "mergedocs"

    def handle(self, *args, **options):
        # for each repeated document
        for dupedoc in Subscriber.objects.values('document').\
                annotate(Count('id')).order_by().filter(document__isnull=False,
                id__count__gt=1):
            try:
                # obtain a subscriber with this document and costumer_id set
                costumer = Subscriber.objects.get(document=dupedoc['document'],
                    costumer_id__isnull=False)
                # iterate over the others and merge fileds into the costumer
                for s in Subscriber.objects.filter(document=dupedoc['document'],
                        costumer_id__isnull=True):
                    # merge the fields for the user object that can be blank
                    for f in ('first_name', 'last_name', 'email'):
                        try:
                            sf = getattr(s.user, f)
                        except AttributeError:
                            # subscriber without user, can be deleted now
                            delete_bastard(s)
                            break
                        if sf and not getattr(costumer.user, f):
                            setattr(costumer.user, f, sf)
                            costumer.user.save()
                            print("Merging %s from %s to %s" % (f, s, costumer))
                    # set password if has user (loop not broken) and if required
                    else:
                        if not is_password_usable(costumer.user.password) and \
                                is_password_usable(s.user.password):
                            costumer.user.password = s.user.password
                            costumer.user.save()
                            print("Merging password from %s to %s" % (s,
                                costumer))
                # iterate again to check email field and deletion
                for s in Subscriber.objects.filter(document=dupedoc['document'],
                        costumer_id__isnull=True):
                    if not costumer.user.email:
                        # if email still blank set username if is a valid email
                        try:
                            validate_email(s.user.username)
                            costumer.user.email = s.user.username
                            costumer.user.save()
                            print("Merging username from %s to %s's email" % \
                                (s, costumer))
                        except ValidationError:
                            pass
                    # delete the bastards
                    delete_bastard(s.user)
                # activate and email the user with the resultant account
                if not costumer.user.is_active:
                    costumer.user.is_active = True
                    costumer.user.save()
                    print("Activating %s" % costumer)
                ctx = {'email': costumer.user.email}
                if costumer.user.username != costumer.user.email and not \
                        costumer.user.username.isdigit():
                    ctx['username'] = costumer.user.username
                costumer.user.email_user(
                    '[ladiaria.com.uy] Tu cuenta de usuario',
                    render_to_string(
                        'notifications/validation_email.html', ctx))
            except Subscriber.DoesNotExist:
                print("Ningún suscriptor con id de cliente con documento %s" \
                    % dupedoc)
            except MultipleObjectsReturned, e:
                print(e.message)
