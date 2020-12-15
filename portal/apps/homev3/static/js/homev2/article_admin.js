var prepareFields = function(){
    var art_type = $('#id_type').val();
    if(art_type == 'HT' || art_type == 'RE'){
        $('#id_body').attr('rows', '20');
        $('.form-row.field-headline').hide();
        $('.form-row.field-deck').hide();
        $('.form-row.field-lead').hide();
        $('.form-row.field-home_lead').hide();
        $('.form-row.field-home_top').hide();
        $('.form-row.field-home_display').hide();
        $('.form-row.field-keywords').hide();
        $('.form-row.field-continues').hide();
        $('.form-row.field-tags').hide();
        $('.form-row.field-location').parent('fieldset').hide();
        $('.form-row.field-gallery').parent('fieldset').hide();
        $('.inline-group').hide();
        $('.form-row.field-body').show();
        if(art_type == "HT"){
            $('#article_form').submit(function(){
                $('#id_headline').val('html');
                $('#id_slug').val('html');
            });
        } else if(art_type == "RE"){
            $('.form-row.field-headline').show();
            $('.form-row.field-lead').show();
            $('#article_form').submit(function(){
                $('#id_slug').val('RECUADRO-' + $('#id_section').val());
                // $('#id_body').val('RECUADRO');
            });
        }
    }
    else {
        $('#id_body').attr('rows', '20');
        $('.form-row.field-headline').show();
        $('.form-row.field-deck').show();
        $('.form-row.field-lead').show();
        $('.form-row.field-home_lead').show();
        $('.form-row.field-home_top').show();
        $('.form-row.field-home_display').show();
        $('.form-row.field-keywords').show();
        $('.form-row.field-continues').show();
        $('.form-row.field-tags').show();
        $('.form-row.field-location').parent('fieldset').show();
        $('.form-row.field-gallery').parent('fieldset').show();
        $('.inline-group').show();
        $('.form-row.field-body').show();
    }

    $('#homearticle_set-group').hide();
    $('div.inline-group div.inline-related').each(function(){
        var fs = $(this).find('fieldset');
        var h2 = $(this).find('h2:first');

        // Don't collapse if fieldset contains errors
        fs.addClass('collapse' + fs.find('div').hasClass('errors')?' collapsed':'');

        // Add toggle link
        var a = $('<a class="collapse-toggle" href="#" style="display:inline;">' + gettext('Show') + '</a>');
        h2.append(a);
        a.before(' (').after(')');
        a.click(function(event){
            event.preventDefault();
            if (!fs.hasClass('collapsed')){
                fs.addClass('collapsed');
                $(this).html(gettext('Show'));
            } else {
                fs.removeClass('collapsed');
                $(this).html(gettext('Hide'));
            }
        }).css('cursor', 'pointer');
        return;
    });
    var div_body = $('#id_body').closest('.form-row');
    var div_body_clone = div_body.clone();
    div_body_clone.html($('#extensions-group'));
    div_body.after(div_body_clone);
}

$(function(){
    prepareFields();
    $("#id_type").change(prepareFields);
    $.each($(".field-main input"), function(index, value){
        $(value).attr('name', 'main_section_radio');
        $(value).attr('data-articlerel-id', $("#id_articlerel_set-" + index + "-id").val());
        $(value).val(index);
        var main_section_selected = $("#id_main_section").val();
        if(main_section_selected && main_section_selected == $(value).attr('data-articlerel-id')){
            $(value).attr('checked', true).parents("tr").addClass('row-articlerel-selected');
        }
        $(value).change(function(){
            $("#id_main_section").val($(this).attr('data-articlerel-id'));
            $(this).parents("tr").addClass('row-articlerel-selected');
            $("[name=main_section_radio]:not(:checked)").parents("tr").removeClass('row-articlerel-selected');
        });
    });
});
