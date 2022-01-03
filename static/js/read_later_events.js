// read later in cards click events
function read_later_events(article_ct_id){
  $('.ld-card__addtrl').click(function(){
    var rl_elem = $(this);
    if(rl_elem.hasClass('added')){
      $.get("/activity/unfollow/" + article_ct_id + "/" + rl_elem.attr('data-article-id') + "/", function(data){
        rl_elem.attr('title', 'Guardar para leer después');
        rl_elem.removeClass('added');
      });
    } else {
      $.get("/activity/follow/" + article_ct_id + "/" + rl_elem.attr('data-article-id') + "/", function(data){
        rl_elem.attr('title', 'Quitar de leer después');
        rl_elem.addClass('added');
      });
    }
  });
}
