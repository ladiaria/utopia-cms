if (window.jQuery) {
  $(function(){
    var toggleExpand = function () {
      expand_btn = $(this);
      if (expand_btn.hasClass("expanded")) {
        expand_btn.removeClass("expanded");
        expand_btn.text("\u21D3");
        var expand = false;
      } else {
        expand_btn.addClass("expanded");
        expand_btn.text("\u21D1");
        var expand = true;
      }
      var main_martor = expand_btn.closest(".main-martor");
      var mbody = $(".martor-field", main_martor);
      var set_height = 400;  // default
      var max_height = $("div.ace_scrollbar-v div.ace_scrollbar-inner", main_martor).height();
      if (max_height > set_height && mbody.height() < max_height && expand) set_height = max_height;
      mbody.attr("style", "height:" + set_height + "px !important");
      $("div.ace_scrollbar-v", main_martor).css("height", set_height + "px");
      $("div.ace_content", main_martor).css("height", set_height + 28 + "px");
      window.dispatchEvent(new Event("resize"));
    };
    // Semantic: button exists in template, no action needed.
    // Bootstrap: no button, add them to gain the feature expand that doesn't come by default in the bootstrap theme
    if ($(".main-martor .expand-editor").length === 0) {
      // create containers for the buttons if they don't exist
      $.each($("div[id^='nav-editor-']"), function() {
        if ($("div.charcounter", this).length === 0) {
          $(this).append($('<div class="charcounter"></div>'));
        }
      });
      // create the buttons
      $(".martor-field").next("textarea").next("div.charcounter").append(
        $("<span>\u21D3</span>").addClass("expand-editor").attr({title: "Expand editor", ariaLabel: "Expand editor"})
        .css({float: "right", cursor: "pointer"})
      );
      // attach click event for all buttons in page, even those added by clicking "new formsets"
      $(document).on("click", ".main-martor .expand-editor", toggleExpand);
    }
    // Ctrl+F / Cmd+F: let browser default (find) run. Capture phase so we run before Ace; stopPropagation so Ace
    // doesn't consume it; we do NOT preventDefault.
    // NOTE: this will run every time the keys are pressed inside a martor field because is the only way to prevent ace
    //       js errors in conjunction to make Ctrl+F run the default browser find.
    if ($(".main-martor").length > 0) {
      document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'F')) {
          var el = e.target && e.target.closest ? e.target.closest('.main-martor') : null;
          if (el) {
            e.stopPropagation();
            // default (browser find) still runs because we didn't preventDefault()
          }
        }
      }, true);
    }
  });
}
