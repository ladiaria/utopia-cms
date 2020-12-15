# -*- coding: utf-8 -*-
from thedaily.forms import SignupForm

from django.template import Library, loader

register = Library()
SIGNUP_TEMPLATE = 'thedaily/templates/signup_form.html'

@register.simple_tag
def signup_form():
    signup_form = SignupForm()
    signup_html = loader.render_to_string(
        SIGNUP_TEMPLATE, {'form': signup_form})
    return signup_html
