// overrided from django admin and updated to fix the "toggle" event handling that was removed in jquery1.9
(function($) {
	// Define this helper to use the original code with a minimal change.
	// Taken from: https://stackoverflow.com/a/25150375/2292933
	$.fn.toggleClick = function() {
		var functions = arguments, iteration = 0;
		return this.click(function() {
			functions[iteration].call();
			iteration = (iteration + 1) % functions.length;
		});
	};
	$(document).ready(function() {
		// Add anchor tag for Show/Hide link
		$("fieldset.collapse").each(function(i, elem) {
			// Don't hide if fields in this fieldset have errors
			if ($(elem).find("div.errors").length == 0) {
				$(elem).addClass("collapsed").find("h2").first().append(' (<a id="fieldsetcollapser' +
					i +'" class="collapse-toggle" style="cursor:pointer;color:#5b80b2">' + gettext("Show") +
					'</a>)');
			}
		});
		// Add toggle to anchor tag
		$("fieldset.collapse a.collapse-toggle").each(function(i, elem) {
			$(elem).toggleClick(
				function() { // Show
					$(elem).text(gettext("Hide")).closest("fieldset").removeClass("collapsed").trigger("show.fieldset", [$(elem).attr("id")]);
					return false;
				},
				function() { // Hide
					$(elem).text(gettext("Show")).closest("fieldset").addClass("collapsed").trigger("hide.fieldset", [$(elem).attr("id")]);
					return false;
				}
			);
		});
	});
})(jQuery);
