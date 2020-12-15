from django.forms.widgets import TextInput
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.safestring import mark_safe


class TagAutocompleteTagIt(TextInput):
    
    def __init__(self, max_tags, *args, **kwargs):
        self.max_tags = max_tags if max_tags else getattr(settings, 'TAGGING_AUTOCOMPLETE_MAX_TAGS', 20)
        super(TagAutocompleteTagIt, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        """ Render HTML code """
        # django-tagging
        case_sensitive = 'true' if not getattr(settings, 'FORCE_LOWERCASE_TAGS', False) else 'false'
        max_tag_lentgh = getattr(settings, 'MAX_TAG_LENGTH', 50)
        # django-tagging-autocomplete-tagit
        autocomplete_min_length = getattr(settings, 'TAGGING_AUTOCOMPLETE_MIN_LENGTH', 1)
        remove_confirmation = 'true' if getattr(settings, 'TAGGING_AUTOCOMPLETE_REMOVE_CONFIRMATION', True) else 'false'
        animate = 'true' if getattr(settings, 'TAGGING_AUTOCOMPLETE_ANIMATE', True) else 'false'
        
        list_view = reverse('tagging_autocomplete_tagit-list')
        html = super(TagAutocompleteTagIt, self).render(name, value, attrs)
        # Subclass this field in case you need to add some custom behaviour like custom callbacks
        js = u"""<script type="text/javascript">init_jQueryTagit({
                objectId: '%s',
                sourceUrl: '%s',
                fieldName: '%s',
                minLength: %s,
                removeConfirmation: %s,
                caseSensitive: %s,
                animate: %s,
                maxLength: %s,
                maxTags: %s,
                onTagAdded  : null,
                onTagRemoved: null,
                onTagClicked: null,
                onMaxTagsExceeded: null,
            })
            </script>""" % (attrs['id'], list_view, name, autocomplete_min_length, remove_confirmation, case_sensitive,
                            animate, max_tag_lentgh, self.max_tags)
        return mark_safe("\n".join([html, js]))
    
    class Media:
        # JS Base url defaults to STATIC_URL/jquery-autocomplete/
        js_base_url = getattr(settings, 'TAGGING_AUTOCOMPLETE_JS_BASE_URL', '%sjs/jquery-tag-it/' % settings.STATIC_URL)
        # jQuery ui is loaded from google's CDN by default
        jqueryui_default = 'https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.12/jquery-ui.min.js'
        jqueryui_file = getattr(settings, 'TAGGING_AUTOCOMPLETE_JQUERY_UI_FILE', jqueryui_default)
        # if a custom jquery ui file has been specified
        if jqueryui_file != jqueryui_default:
            # determine path
            jqueryui_file = '%s%s' % (js_base_url, jqueryui_file)
        
        # load js
        js = (
            '%stagging_autocomplete_tagit.js' % js_base_url,
            jqueryui_file,
            '%sjquery.tag-it.min.js' % js_base_url,            
        )
        
        # custom css can also be overriden in settings
        css_list = getattr(settings, 'TAGGING_AUTOCOMPLETE_CSS', ['%scss/ui-autocomplete-tag-it.css' % js_base_url])
        # check is a list, if is a string convert it to a list
        if type(css_list) != list and type(css_list) == str:
            css_list = [css_list]
        css = {
            'screen': css_list
        }