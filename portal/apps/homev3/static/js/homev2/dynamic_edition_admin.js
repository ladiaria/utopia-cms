var InlineOrdering = {

    init: function () {

        var inline_group_containers = $('.inline-group').has('.dynamic-order');
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

        function UpdateArticlesPage(section){
            var articles = $(section).find('.dynamic-order > table > tr').not('[id$=-empty]');
            articles.each(function(i,art){
                var art = $(art);
                var input_page = art.find('input[id$=-page]');
                var current_page = art.closest('tbody.page').data('page');
                input_page.val(current_page);
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

        inline_group_containers.not('[id$=-group]').each( function(i, section){
            var section = $(section);
            var orderables = section.find('.dynamic-order > table > tbody > tr').has('td');
            var connector = '.page';

            $('.placeholder').hide();
            section.sortable({
                forcePlaceholderSize: 'true',
                items: orderables,
                connectWith: connector,
                // Some options.
                revert: true,
                start: function(e, ui){
                    ui.placeholder.height(ui.item.height());
                },
                stop: function(event, ui){
                    UpdateArticlesPage(section);
                    UpdateSection(section);
                },
                update: function(event, ui) {
                    page = ui.item.closest('.dynamic-order > table > tbody');
                    if (page.find('tr').not('[id$=-empty]').length > 6 && connector != ''){
                        section.sortable('cancel');
                    }
                },
            });
            orderables.css('cursor', 'move');
            $('td.field-order input').hide();
        });

        inline_group_containers.each( function(){
            var section = $(this);
            var orderables = section.find('.dynamic-order > table > tbody > tr').has('td');
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

        $('.inline-group').each( function(group_id){
            var group = $(this);
            group.find('.field-home_top').each(function(i){
                $(this).prepend($("<div class=''>Destacado</div>"));
            });
        });

        $('form').submit(function(){
            inline_group_containers.each( function(){
                var container = $(this);
                var i = 0;
                if(container.find('tr[id^=articlerel_set]').length > 0){
                    var order_field = 'top_position';
                    // TODO: explain better the next comment:
                    // For fix the entire page uncomment these lines and build the section for store
                    /*if(container.find('h2:contains("Nota de tapa y titulines")').length > 0){
                        var order_field = 'top_position';
                    } else {
                        var order_field = 'position';
                    }*/
                    var tr_elem = container.find('tr[id^=articlerel_set]').filter('.has_original');
                }
                else if(container.find('tr[id^=categorynewsletterarticle_set]').length > 0){
                    var order_field = 'order';
                    var tr_elem = container.find('tr[id^=categorynewsletterarticle_set]').filter('.has_original');
                }
                else if(container.find('tr[id^=categoryhomearticle_set]').length > 0){
                    var order_field = 'position';
                    var tr_elem = container.find('tr[id^=categoryhomearticle_set]').filter('.has_original');
                }
                else{
                    var order_field = '#';  // not matched character
                    var tr_elem = $(this);
                }

                tr_elem.not('tr[id$=-empty]').each( function(){
                    var input_find = ['input[id$=', order_field, ']'].join('');
                    var order_input = $(this).find(input_find);
                    // Pone en 0 antes del submit si no tiene article
                    if ($(this).find('input[id$=headline]').val() == ''){
                        order_input.val(0);
                    } else {
                        i++;
                        order_input.val(i);
                    }
                });
            });
        });
    },
};

var SectionIds = {
    init: function () {
        var inline_group_containers = $('.inline-group').has('.dynamic-order');
        inline_group_containers.not('[id$=-group]').each(function(){
            var div = $(this);
            var title = $(div.find('h2'));
            var text = title.html();
            var section_id = text.match(/[^\[/\[]+(?=\]\])/g);
            title.html(text.replace('[[' + section_id + ']]',""));
            div.attr('data-section_id', section_id);
        });
    },
};

var last_clicked_inline;
var last_section_id;

// cambia el link de crear un inline por un popup y agrega link de elegir artículo existente
var PopUpAdd = {
    init: function () {
        $('div.add-row a').each(function(){
            var add_link = $(this);
            if(add_link.closest('div[id^=articlerel_set-].inline-group').length > 0){
                var cover_group = add_link.closest('div[id^=articlerel_set-].inline-group');
            }
            else if (add_link.closest('div[id^=categorynewsletterarticle_set-].inline-group').length > 0){
                var cover_group = add_link.closest('div[id^=categorynewsletterarticle_set-].inline-group');
            }
            else if (add_link.closest('div[id^=categoryhomearticle_set-].inline-group').length > 0){
                var cover_group = add_link.closest('div[id^=categoryhomearticle_set-].inline-group');
            }
            else {
                var cover_group = undefined;
            }
            var section_id = cover_group.attr('data-section_id');
            var pub_id = $('#id_publication').val();
            add_link.off("click");
            add_link.on("click", function(){
                return showAddAnotherPopup(this);
            });
            var choose_link = add_link.clone();
            add_link.after(choose_link);
            choose_link.html('Elegir un Articulo existente');
            choose_link.attr('href', '/admin/core/article/?t=id');
            choose_link.on("click", function(){
                last_clicked_inline = add_link;
                last_section_id = section_id;
                return showRelatedObjectLookupPopup(this);
            });
            choose_link.css('margin-left','24px');
            // replace the div container by a tr
            add_link.parent().replaceWith('<tr class="add-row"><td colspan="5">' + add_link.parent().html() + '</td></tr>');
        });
    },
};

// Set up for tables and behavior based on the view that is present
var SetUp = {
    init: function () {
        // based on views that are being presented
        if ($('div[id^=categoryhomearticle_set-]').length){
            $("th:contains('Orden')").show();
            $('td[class$=-top_position]').show();
            $('td[class$=-position]:not(:has(.errorlist))').show();
        }
        else {
            $("th:contains('Orden')").hide();
            $('td[class$=-top_position]').hide();
            $('td[class$=-position]:not(:has(.errorlist))').hide();
        }
    },
};


// refresh de la edición cuando se vuelve del popup
function dismissAddAnotherPopup(win, newId, newRepr) {
    win.close();
    location.reload();
};

function dismissRelatedLookupPopupTarget(win, chosenId) {
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
        }
        win.close();
    }

function dismissRelatedLookupPopup(win, article_id){
    dismissRelatedLookupPopupTarget(win, article_id);
}

$(function () {
    $(document).on("load", SetUp.init());
    $(document).on("load", InlineOrdering.init());
    $(document).on("load", SectionIds.init());
    $(document).on("load", PopUpAdd.init());
});
