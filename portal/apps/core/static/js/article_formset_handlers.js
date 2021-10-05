(function($) {
    $(document).on('formset:added', function(event, $row, formsetName) {
        if (formsetName == 'articlerel_set') {
            $("[name=main_section_radio]", $row).change(function(){
                main_section_row_selected($(this));
            });
        }
    });
})(django.jQuery);