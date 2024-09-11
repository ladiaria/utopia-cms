"""
Inherits from the "uni_form" Layout objects to force templates on TEMPLATE_PACK
and  use of Materialize CSS classes
"""
from django.conf import settings
from django.template import Context
from django.template.loader import render_to_string

from crispy_forms.utils import render_field
from crispy_forms import layout as crispy_forms_layout

TEMPLATE_PACK = getattr(settings,
                        'CRISPY_TEMPLATE_PACK',
                        'materialize_css_forms')


class Layout(crispy_forms_layout.Layout):
    pass


class UneditableField(crispy_forms_layout.HTML):
    pass


class HTML(crispy_forms_layout.HTML):
    pass


class MultiWidgetField(crispy_forms_layout.MultiWidgetField):
    pass


class Div(crispy_forms_layout.Div):
    """
    It wraps fields in a <div>

    You can set ``css_id`` for a DOM id and ``css_class`` for a DOM class.
    Example:

    .. sourcecode:: python

        Div('form_field_1', 'form_field_2', css_id='div-example', css_class='divs')
    """
    template = "{0}/layout/div.html".format(TEMPLATE_PACK)


class Row(Div):
    """
    It wraps fields in a div whose default class is ``row``.
    Example:

    .. sourcecode:: python

        Row('form_field_1', 'form_field_2', 'form_field_3')

    Act as a div container row, it will embed its items in a div like that:

    .. sourcecode:: html

        <div class"row">Your stuff</div>
    """
    css_class = 'row'


class Column(Div):
    """
    .. _http://materializecss.com/grid.html

    It wraps fields in a div. If not defined, CSS class will default to
    ``col s12``. ``col`` class is always appended, so you don't
    need to specify it.

    This is the column from the `Materialize CSS`_, all columns should be
    contained in a **Row** and you will have to define the
    column type in the ``css_class`` attribute.

    Example:

    .. sourcecode:: python

        Column('form_field_1', 'form_field_2', css_class='s6')

    Will render to something like that:

    .. sourcecode:: html

        <div class"col s6">...</div>

    ``col`` class is always appended, so you don't need to specify it.

    If not defined, ``css_class`` will default to ``s12``.
    """
    css_class = 'col'

    def __init__(self, field, *args, **kwargs):
        self.field = field
        if 'css_class' not in kwargs:
            kwargs['css_class'] = 's12'

        super(Column, self).__init__(field, *args, **kwargs)


class Field(crispy_forms_layout.Field, Div):
    """
    Layout object, It contains one field name, and you can add attributes to
    it easily. For setting class attributes, you need to use `css_class`,
    as `class` is a Python keyword.

    Example:

    .. sourcecode:: python

        Field('field_name', style="color: #333;",
            css_class="whatever", id="field_name")
    """
    template = "{0}/field.html".format(TEMPLATE_PACK)


class FileField(Field):
    """
    Field that exposes a file upload button in the materialize way
    """
    def __init__(self, field, *args, **kwargs):
        self.field = field
        if 'css_class' not in kwargs:
            kwargs['css_class'] = 'file-path validate'

        super(FileField, self).__init__(field, *args, **kwargs)

    template = "{0}/field.file.html".format(TEMPLATE_PACK)

class MultiField(crispy_forms_layout.MultiField):
    """
    MultiField container. Renders to a MultiField
    """
    template = "{0}/layout/multifield.html".format(TEMPLATE_PACK)
    field_template = "{0}/multifield.html".format(TEMPLATE_PACK)


class InlineField(Field):
    """
    Layout object for rendering an inline field with Materialize

    Example:

    .. sourcecode:: python

        InlineField('field_name')

    Or:

    .. sourcecode:: python

        InlineField('field_name', label_column='large-8',
        input_column='large-4', label_class='')

    ``label_column``, ``input_column``, ``label_class``, are optional argument.
    """
    template = "{0}/layout/inline_field.html".format(TEMPLATE_PACK)

    def __init__(self, field, label_column='large-3', input_column='large-9',
                 label_class='', *args, **kwargs):
        self.field = field
        self.label_column = label_column+' columns'
        self.input_column = input_column+' columns'
        self.label_class = label_class

        super(InlineField, self).__init__(field, *args, **kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        context['label_column'] = self.label_column
        context['input_column'] = self.input_column
        context['label_class'] = self.label_class

        html = ''
        for field in self.fields:
            html += render_field(field, form, form_style, context,
                                 template=self.template, attrs=self.attrs,
                                 template_pack=template_pack)
        return html


class Button(crispy_forms_layout.Button):
    """
    Used to create a Submit input descriptor for the {% crispy %} template tag:

    .. sourcecode:: python

        button = Button('Button 1', 'Press Me!')

    .. note:: The first argument is also slugified and turned into the
    id for the button.
    """
    input_type = 'button'
    field_classes = 'btn waves-effect waves-light'


class Submit(crispy_forms_layout.Submit):
    """
    Used to create a Submit button descriptor for the {% crispy %}
    template tag:

    .. sourcecode:: python

        submit = Submit('Search the Site', 'search this site')

    .. note:: The first argument is also slugified and turned into the id for the submit button.
    """
    input_type = 'submit'
    field_classes = 'btn waves-effect waves-light'


class Hidden(crispy_forms_layout.Hidden):
    """
    Used to create a Hidden input descriptor for the {% crispy %} template tag.
    """
    input_type = 'hidden'
    field_classes = 'hidden'
