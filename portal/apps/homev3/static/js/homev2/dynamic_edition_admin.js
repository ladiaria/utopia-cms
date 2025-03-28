/*
 * TODO: is the "page" concept here still valid? if not, remove or try to rename to a better name.
 */
var InlineOrdering = {

  init: function () {

  // Rompemos el tbody para hacer multiples tbody. (TODO: explain why)
  $('.inline-group > .dynamic-order > table > tbody').contents().unwrap();

  function UpdatePages(section){
    var table = $(section).find('.dynamic-order > table');
    var pages = table.find('> tbody');
    pages.each(function(i,page){
      var page = $(page);
      if (page.children().length = 0){
        page.remove();
      }
    });
    pages.sort(function(a,b){
      return parseFloat(a.dataset.page) > parseFloat(b.dataset.page);
    }).appendTo(table);
  }

  // agrupamos
  $('.inline-group').each(function(){
    UpdatePages($(this));
  });

  // Al cambiar el número de página se hace update (TODO: what is called a "page" here?, see TODO in the top this file)
  $( "input[id$=-page]" ).change(function() {
    var section = $(this).closest('.inline-group');
    var new_page = $(this).val();
    var current_page = $(this).closest('tbody').data('page');
    var arts_count = section.find('.dynamic-order > table > tbody[data-page="' + new_page + '"]').find('tr').not('[id$=-empty]').length;

    if (arts_count > 5){
      $(this).val(current_page);
    } else {
      UpdatePages(section);
    }
  });

  var inline_group_containers = $('fieldset.dynamic-order');
  inline_group_containers.each( function(){
    var section = $(this);
    var orderables = section.find('table > tbody > tr').has('td');
    section.sortable({
      axis: 'y',
      placeholder: 'ui-state-highlight',
      forcePlaceholderSize: 'true',
      items: orderables,
      update: function(event, ui) {
        UpdatePages(section);
      },
    });
    orderables.css('cursor', 'move');
    $('td.field-order input').hide();
  });

  $('form').submit(function(){
    inline_group_containers.each(function(){
      var container = $(this);
      if (container.find('tr[id^=articlerel_set]').length > 0) {
        var order_field = (
          $('h2:contains("Artículos en portada")', container).length ? 'top_' : ''
        ) + 'position';
        var tr_elem = container.find('tr[id^=articlerel_set]');
      } else if(container.find('tr[id^=categorynewsletterarticle_set]').length > 0){
        var order_field = 'order';
        var tr_elem = container.find('tr[id^=categorynewsletterarticle_set]').filter('.has_original');
      } else if(container.find('tr[id^=categoryhomearticle_set]').length > 0){
        var order_field = 'position';
        var tr_elem = container.find('tr[id^=categoryhomearticle_set]').filter('.has_original');
      } else {
        var order_field = '#';  // not matched character
        var tr_elem = $(this);
      }
      tr_elem.not('tr[id$=-empty]').each(function(){
        var input_find = ['input[id$=', order_field, ']'].join('');
        var order_input = $(this).find(input_find);
        // NOTE: next commented line is useful to debug, keep it for now
        // console.log(order_field + " iteration to set value in: " + order_input.attr('id'));
        // Set field to its row index or zero if no article
        if ($(this).find('input[id$=headline]').val() == ''){
          order_input.val(0);
        } else {
          order_input.val($(this).index() + 1);
        }
      });
    });
  });
  },
};

$(function () {
  $(document).on("load", InlineOrdering.init());
});
