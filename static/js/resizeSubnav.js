// submenu more for brands and categories
function resizeSubnav(container, primary, more) {
    container.addClass('js');
    if( more == 1){
      primary.append('<li class="more"><button type="button" aria-haspopup="true" aria-expanded="false" aria-label="Mostrar todas las categorías"><svg xmlns="http://www.w3.org/2000/svg" width="38" height="20" viewBox="0 0 38 20"><rect width="38" height="20" rx="10" fill="#fff" opacity="0.5"/><g transform="translate(-674.803 -4175.101)"><circle cx="2" cy="2" r="2" transform="translate(699.803 4183.101)" fill="#262626"/><circle cx="2" cy="2" r="2" transform="translate(691.803 4183.101)" fill="#262626"/><circle cx="2" cy="2" r="2" transform="translate(683.803 4183.101)" fill="#262626"/></g></svg></button></li>');
    }else if( more == 2){
      primary.append('<li class="more"><button type="button" aria-haspopup="true" aria-expanded="false" aria-label="Mostrar todas las categorías"><svg xmlns="http://www.w3.org/2000/svg" width="38" height="20" viewBox="0 0 38 20"><g transform="translate(-17097 639)"><rect width="38" height="20" rx="10" transform="translate(17097 -639)" fill="#eee"/><g transform="translate(16422.197 -4814.101)"><circle cx="2" cy="2" r="2" transform="translate(699.803 4183.101)" fill="#262626"/><circle cx="2" cy="2" r="2" transform="translate(691.803 4183.101)" fill="#262626"/><circle cx="2" cy="2" r="2" transform="translate(683.803 4183.101)" fill="#262626"/></g></g></svg></button></li>');
    }

    container.append('<ul class="secondary"></ul>');
    var primaryItems = $('> li:not(.more)', primary);

    var allItems = $('li', primary);
    var moreLi = $('.more', primary);
    var moreBtn = $('button', moreLi);
    moreBtn.click( function(){
      container.toggleClass('show-secondary');
      moreBtn.attr('aria-expanded', primary.hasClass('show-secondary'));
      moreBtn.remove(primary.hasClass('show-secondary'));
      return false;
    });

    allItems.each(function(){
      $(this).removeClass('.hidden');
    });

    var secondaryItems = [];
    var stopWidth = moreBtn.outerWidth(true);
    var primaryWidth = container.width();

    primaryItems.each(function(){
      if(primaryWidth >= stopWidth + $(this).outerWidth(true)) {
        stopWidth += $(this).outerWidth(true);
      } else {
        secondaryItems.push($(this));
        $(this).addClass('hidden');
      }
    });

    if(secondaryItems.length === 0)  {
      moreLi.addClass('hidden');
      container.removeClass('show-secondary');
      moreBtn.attr('aria-expanded', false);
    }else {
      primary.addClass('full');
    }

    $.each(secondaryItems, function(i){
      $(this).removeClass('hidden');
      $('.secondary', container).append($(this));
    });
  }