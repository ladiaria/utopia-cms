if (window.jQuery) {
  $(function(){
    var runExpand = function () {
      var mbody = $(".martor-field");
      var set_height = 400;  // default
      var max_height = $("div.ace_scrollbar-v div.ace_scrollbar-inner").height();
      if (max_height > set_height && mbody.height() < max_height) set_height = max_height;
      mbody.attr("style", "height:" + set_height + "px !important");
      $("div.ace_scrollbar-v").css("height", set_height + "px");
      $("div.ace_content").css("height", set_height + 28 + "px");
      window.dispatchEvent(new Event("resize"));
    };
    // Semantic: button exists in template. Bootstrap: no button, we add one so Ctrl+F can work with native find.
    if ($(".main-martor .expand-editor").length === 0) {
      $(".martor-field").next("textarea").next("div.charcounter").append(
        $("<span>\u21D3</span>").addClass("expand-editor").attr({title: "Expand editor", ariaLabel: "Expand editor"})
        .css({float: "right", cursor: "pointer"}).on("click", runExpand)
      );
    }
    // Ctrl+F / Cmd+F: let browser default (find) run. Capture phase so we run before Ace; stopPropagation so Ace
    // doesn't consume it; we do NOT preventDefault.    //
    // TODO: let this exec only once, a 2nd time makes no sense.
    //       try to write it using jquery event.on() and event.off(). In jquery, how to pass the last "true" parameter?
    //       do this will work for more than one martor field in the page?
    //       explain why we can't just "run now" but need to wait to do this until the keys are pressed by 1st time.
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'F')) {
        var el = e.target && e.target.closest ? e.target.closest('.main-martor') : null;
        if (el) {
          e.stopPropagation();
          // default (browser find) still runs because we didn't preventDefault()
        }
      }
    }, true);
  });
}
