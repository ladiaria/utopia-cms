$(function () {
	  $(document).load(
		function(){
	  		$('a[href="/admin/core/article/"]').attr('href',"/admin/core/article/?type__exact=NE");
	  		}()
	  );
});
