import sys

from django.conf import settings
from django.template.loader import render_to_string

from inplaceeditform.commons import apply_filters
from inplaceeditform.fields import BaseAdaptorField

from bootstrap3_datetime.widgets import DateTimePicker

if sys.version_info.major == 2:
    string = basestring
else:
    string = str
    unicode = str


class BaseAdaptorDateBootStrapField(BaseAdaptorField):

    def __init__(self, *args, **kwargs):
        super(BaseAdaptorDateBootStrapField, self).__init__(*args, **kwargs)
        self.config['can_auto_save'] = 0

    def get_field(self):
        field = super(BaseAdaptorDateBootStrapField, self).get_field()
        field.field.widget = DateTimePicker(options=self.options)
        return field

    def render_value(self, field_name=None):
        val = super(BaseAdaptorDateBootStrapField, self).render_value(field_name)
        if not isinstance(val, string):
            val = apply_filters(val, [self.filter_render_value])
        return val

    def render_value_edit(self):
        value = super(BaseAdaptorDateBootStrapField, self).render_value_edit()
        field = self.get_field()
        if not value:
            value = self.empty_value()
        if not getattr(self.request, 'inplace_js_rendered', None):
            if getattr(self.request, 'inplace_js_extra', None) is None:
                self.request.inplace_js_extra = ''
            scripts = ''.join(field.field.widget.media.render_js())
            if not scripts in self.request.inplace_js_extra:
                self.request.inplace_js_extra += scripts
            return value
        return render_to_string('inplaceeditform_bootstrap/adaptor_date/render_value_edit.html',
                                {'value': value,
                                 'adaptor': self,
                                 'field': self.get_field(),
                                 'is_ajax': self.request.is_ajax()})


class AdaptorDateBootStrapField(BaseAdaptorDateBootStrapField):

    @property
    def name(self):
        return 'date_bootstrap'

    def __init__(self, *args, **kwargs):
        super(AdaptorDateBootStrapField, self).__init__(*args, **kwargs)
        self.filter_render_value = "date:'%s'" % settings.DATE_FORMAT
        self.options = {"format": "yyyy-MM-dd",
                        "pickTime": False}


class AdaptorDateTimeBootStrapField(BaseAdaptorDateBootStrapField):

    @property
    def name(self):
        return 'datetime_bootstrap'

    def __init__(self, *args, **kwargs):
        super(AdaptorDateTimeBootStrapField, self).__init__(*args, **kwargs)
        self.filter_render_value = "date:'%s'" % settings.DATETIME_FORMAT
        self.options = {}
