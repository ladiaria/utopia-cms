var InlineOrdering = {

  init: function () {

  // hide order column in category newsletters
  if ($('#categorynewsletter_form').length) {
    $("th.column-order").css('visibility', 'hidden');
  }

  // Rompemos el tbody para hacer multiples tbody.
  $('.inline-group > .dynamic-order > table > tbody').contents().unwrap();
    var MakePages = function(section){
    var section = $(section);
    var section_id = section.data('section_id');
    var articles = section.find('.dynamic-order > table tr').not('[id$=-empty]');
    $(articles).each( function(i, art){
      var art = $(art);
      var new_page = art.find("input[id$=-page]").val();
      var page = art.closest('.dynamic-order > table').find('tbody[data-page="' + new_page + '"]');
      var exists = page.length != 0;
      if (page != new_page || page == 'undefined'){
        var tbody = art.closest('.dynamic-order > table').find('tbody[data-page="' + new_page + '"]');
        var exists = tbody.length != 0;
        var articles_count = tbody.find('.dynamic-order > table tr').not('[id$=-empty]');
        if (exists && articles_count.length < 6){
          tbody.append(art);
        }else{
          if (articles_count.length > 6){
            new_page = new_page + "1";
          }
          art.closest('.dynamic-order > table').append('<tbody class="page page_' + new_page + '" data-page="' + new_page + '"></tbody>');
          parent_tbody = art.closest('.dynamic-order > table').find('tbody[data-page="' + new_page + '"]');
          parent_tbody.append(art);
          art.attr('data-page', new_page);
        }
      }
    });
  };

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

  function UpdateSection(section){
    MakePages(section);
    UpdatePages(section);
  }

  // agrupamos
  $('.inline-group').each(function(){
    UpdateSection($(this));
  });

  // Al cambiar el número de página se hace update
  $( "input[id$=-page]" ).change(function() {
    var section = $(this).closest('.inline-group');
    var new_page = $(this).val();
    var current_page = $(this).closest('tbody').data('page');
    var arts_count = section.find('.dynamic-order > table > tbody[data-page="' + new_page + '"]').find('tr').not('[id$=-empty]').length;

    if (arts_count > 5){
      $(this).val(current_page);
    } else {
      UpdateSection(section);
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
        UpdateSection(section);
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
          order_input.val($(this).index());
        }
      });
    });
  });
  },
};

// refresh de la edición cuando se vuelve del popup
function dismissAddAnotherPopup(win, newId, newRepr) {
  win.close();
  location.reload();
};

function dismissRelatedLookupPopupTarget(win, chosenId, chosenText) {
  /*
  Convert open window name into an django html element ID format.
  Find element by ID if it's vManyToManyRawIdAdminField attach given ID to the value.
  Otherwise, set the given ID to the value of the target element
  */
  var name = windowname_to_id(win.name);
  var elem = window.document.getElementById(name);
  if (elem){
    if (elem.className.indexOf('vManyToManyRawIdAdminField') !== -1 && elem.value) {
      elem.value += ',' + chosenId;
    } else {
      var is_empty = (elem.value) ? false: true;
      elem.value = chosenId;
      // add class to the parent tr for prevent default order for the new row added, and keep the selected order
      if(is_empty){
        $('#' + name).closest('tr').addClass('has_original');
      }
    }
    // Update the <strong> element next to the input with the chosen text
    var strongElement = $('#' + name).closest('td').find('strong');
    if (strongElement.length > 0) {
      strongElement.text(chosenText); // Set the text of the <strong> element
    }
  }
  win.close();
}

function dismissRelatedLookupPopup(win, article_id, chosenText){
  dismissRelatedLookupPopupTarget(win, article_id, chosenText);
}

$(function () {
  $(document).on("load", InlineOrdering.init());
});
