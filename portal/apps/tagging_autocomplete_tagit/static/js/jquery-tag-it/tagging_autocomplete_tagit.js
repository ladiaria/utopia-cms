// this should make it work both in the admin and in the frontend
if(!jQuery) var jQuery = django.jQuery;
// handler
window.django_autocomplete_max_reached = false;
function init_jQueryTagit(options){
    jQuery('#'+options.objectId).tagit({
        singleFieldDelimiter: ', ',
        fieldName         : options.fieldName,
        tagSource         : function(request, response){
            jQuery.getJSON(options.sourceUrl, {
                term: request.term
            }, response);
        },
        minLength         : options.minLength,
        removeConfirmation: options.removeConfirmation,
        caseSensitive     : options.caseSensitive,
        animate: options.animate,
        maxLength: options.maxLength,
        maxTags: options.maxTags,
        // Event callbacks.            
        onTagAdded  : options.onTagAdded,
        onTagRemoved: options.onTagRemoved,
        onTagClicked: options.onTagClicked,
        onMaxTagsExceeded: options.onMaxTagsExceeded,
        allowSpaces: true,
    });
}