/* Copyright (c) 2007 Tom Deater (http://www.tomdeater.com) */
$(function(){
    $('textarea.vLargeTextField').each(function(){
        $(this).charCounter();
    });
});
(function($) {
	$.fn.charCounter = function (settings) {
		settings = $.extend({
			container: "<div></div>",
			classname: "charcounter",
			format: "%1 caracteres",
			delay: 0
		}, settings);
		var p, timeout;

		function count(el, container) {
			el = $(el);
			if (settings.delay > 0) {
				if (timeout) {
					window.clearTimeout(timeout);
				}
				timeout = window.setTimeout(function () {
					container.html(settings.format.replace(/%1/, el.val().length));
				}, settings.delay);
			} else {
				container.html(settings.format.replace(/%1/, el.val().length));
			}
		};

		return this.each(function () {
			var container = (!settings.container.match(/^<.+>$/))
				? $(settings.container)
				: $(settings.container)
					.insertAfter(this)
					.addClass(settings.classname);
			$(this)
				.bind("keydown", function () { count(this, container); })
				.bind("keypress", function () { count(this, container); })
				.bind("keyup", function () { count(this, container); })
				.bind("focus", function () { count(this, container); })
				.bind("mouseover", function () { count(this, container); })
				.bind("mouseout", function () { count(this, container); })
				.bind("paste", function () {
					var me = this;
					setTimeout(function () { count(me, container); }, 10);
				});
			if (this.addEventListener) {
				this.addEventListener('input', function () { count(this, container); }, false);
			};
			count(this, container);
		});
	};

})(jQuery);
