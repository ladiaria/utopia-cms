/*
 * la diaria, 2018
 * Selects all sites by default only if this is the form for a new ad.
 * (for new ads, no viewlink is present in the page)
 */

(function($) {
    $(function(){
        if($('a.viewsitelink').length == 0 && $('#id_sites').length == 1){
            $('#id_sites option').prop('selected', true);
        }
    });
})(django.jQuery);
