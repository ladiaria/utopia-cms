var prepareFields = function(){
  var art_type = $('#id_type').val();
  $('.main-martor').attr('rows', '20');
  $('.form-row.field-body').show();
  if(art_type == 'HT'){
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
    $('#article_form').submit(function(){
      $('#id_headline').val('html');
      $('#id_slug').val('html');
    });
  } else {
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
  }
  $('#homearticle_set-group').hide();
  // custom position for "recuadros" inline (below martor or ckeditor widget, the body field)
  var fset_body = $('.main-martor,div.ck').closest('fieldset');
  fset_body.after($('#recuadros-group'));
};
var main_section_row_selected = function(radio_field){
  radio_field.parents("tr").addClass('row-articlerel-selected');
  $("[name=main_section_radio]:not(:checked)").parents("tr").removeClass('row-articlerel-selected');
};
if (window.jQuery) {
  $(function(){
    prepareFields();
    $("#id_type").on("change", prepareFields);
    $.each($(".field-main input"), function(index, value){
      $(value).attr('name', 'main_section_radio');
      $(value).attr('data-articlerel-id', $("#id_articlerel_set-" + index + "-id").val());
      $(value).val(index);
      var main_section_selected = $("#id_main_section").val();
      if(main_section_selected && main_section_selected == $(value).attr('data-articlerel-id')){
        $(value).attr('checked', true).parents("tr").addClass('row-articlerel-selected');
      }
      $(value).change(function(){
        var rel_id = $(this).attr('data-articlerel-id');
        if (rel_id) {
          $("#id_main_section").val(rel_id);
        }
        main_section_row_selected($(this));
      });
    });
    // sortable inlines handlers (to show the position updated after sorting, to save the position for new rows)
    function sortable2_dragend_handler(table_container_selector) {
      $(table_container_selector + ' tr.has_original').on('dragend', function(event) {
        // update widgets positions labels in the inline
        update_pos_labels(event.target);
      });
    }
    // new/delete rows handlers.
    document.addEventListener('formset:added', (event) => {
      if (event.detail.formsetName == 'recuadros') {
        update_pos_labels(event.target, "");
      }
    });
    document.addEventListener('formset:removed', (event) => {
      if (event.detail.formsetName == 'recuadros') {
        update_pos_labels("#recuadros-group tr", "");
      }
    });
    sortable2_dragend_handler('#recuadros-group');
    // put the unpublish radio beeing part of the publish radio choice group
    $('#id_unpublish_radio_choice_0').prop("name", "publish_radio_choice");
  });
}
