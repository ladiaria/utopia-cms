(function($) {
    $(document).on('formset:added', function(event) {
        if (event.detail.formsetName == 'articlerel_set') {
            $("[name=main_section_radio]", $(event.target)).change(function(){
                main_section_row_selected($(this));
            });
        }
    });
})(django.jQuery);
