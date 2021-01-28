var InlineOrdering = {

    init: function () {
        $("th:contains('Orden')").hide();
        $('td[class$=-top_position]').hide();
        $('td[class$=-position]').hide();

        // Rompemos el tbody para hacer multiples tbody.
        $('.inline-group table > tbody').contents().unwrap();

        var MakePages = function(section){
            var section = $(section);
            var section_id = section.data('section_id');
            var articles = section.find('table tr[id^=articlerel_set]').not('[id$=-empty]');
            $(articles).each( function(i, art){
                var art = $(art);
                var new_page = art.find("input[id$=-page]").val();
                var page = art.closest('table').find('tbody[data-page="' + new_page + '"]');
                var exists = page.length != 0;
                if (page != new_page || page == 'undefined'){
                    var tbody = art.closest('table').find('tbody[data-page="' + new_page + '"]');
                    var exists = tbody.length != 0;
                    var articles_count = tbody.find('table tr[id^=articlerel_set]').not('[id$=-empty]');
                    if (exists && articles_count.length < 6){
                        tbody.append(art);
                    }else{
                        if (articles_count.length > 6){
                            new_page = new_page + "1";
                        }
                        art.closest('table').append('<tbody class="page page_' + new_page + '" data-page="' + new_page + '"></tbody>');
                        parent_tbody = art.closest('table').find('tbody[data-page="' + new_page + '"]');
                        parent_tbody.append(art);
                        art.attr('data-page', new_page);
                    }
                }
            });
        };

        function UpdateArticlesPage(section){
            var articles = $(section).find('tr[id^=articlerel_set]').not('[id$=-empty]');
            articles.each(function(i,art){
                var art = $(art);
                var input_page = art.find('input[id$=-page]');
                var current_page = art.closest('tbody.page').data('page');
                input_page.val(current_page);
            });
        };

        function UpdatePages(section){
            var table = $(section).find('table');
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
            var arts_count = section.find('tbody[data-page="' + new_page + '"]').find('tr[id^=articlerel_set]').not('[id$=-empty]').length;

            if (arts_count > 5){
                $(this).val(current_page);
            } else {
                UpdateSection(section);
            }
        });

        $('div[id^=articlerel_set-].inline-group').not('[id=articlerel_set-group]').each( function(i, section){
            var section = $(section);
            var orderables = section.find('[id^=articlerel_set]');
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
                    page = ui.item.closest('tbody');
                    if (page.find('tr[id^=articlerel_set]').not('[id$=-empty]').length > 6 && connector != ''){
                        section.sortable('cancel');
                    }
                },
            });
            orderables.css('cursor', 'move');
            $('td.field-order input').hide();
        });

        $('#articlerel_set-group').each( function(){
            var section = $(this);
            var orderables = section.find('[id^=articlerel_set]');
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
            $('.inline-group').each( function(){
                var i = 0;
                $(this).find('tr[id^=articlerel_set]').not('tr[id$=-empty]').each( function(){
                    var order_input = $(this).find('input[id$=position]');
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
        $('div[id^=articlerel_set-].inline-group').not('[id=articlerel_set-group]').each(function(){
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
            var section_id = add_link.closest('div[id^=articlerel_set-].inline-group').attr('data-section_id');
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

// refresh de la edición cuando se vuelve del popup
function dismissAddAnotherPopup(win, newId, newRepr) {
    win.close();
    location.reload();
};

function dismissRelatedLookupPopup(win, article_id){
    var last_inline = last_clicked_inline.closest('tbody').prev().prev();
    var new_inline = last_inline.clone();
    last_inline.after(new_inline);
    var a = $('a[href="' + article_id + '/"]', win.document);
    var headline = a.html();
    new_inline.find('input[id$=headline]').val(headline);
    var edition_id = $('#id_articlerel_set-0-edition').val();
    win.close();
    window.location.href = '/admin/core/edition/add_article/' + edition_id + '/' + last_section_id + '/' + article_id + '/';
}

$(function () {
    $(document).on("load", InlineOrdering.init());
    $(document).on("load", SectionIds.init());
    $(document).on("load", PopUpAdd.init());
});
