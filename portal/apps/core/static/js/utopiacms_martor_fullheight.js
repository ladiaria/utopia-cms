if (window.jQuery) {
    $(function(){
        $("span.expand-editor").on("click", function(){
            var mbody = $(".martor-field");
            var set_height = 400;  // default
            var max_height = $("div.ace_scrollbar-v div.ace_scrollbar-inner").height();
            if (max_height > set_height && mbody.height() < max_height) {
                set_height = max_height;
            }
            mbody.attr("style", "height:" + set_height + "px !important");
            $("div.ace_scrollbar-v").css("height", set_height + "px");
            $("div.ace_content").css("heigth", set_height + 28 + "px");
            window.dispatchEvent(new Event("resize"));
        });
    });
}
