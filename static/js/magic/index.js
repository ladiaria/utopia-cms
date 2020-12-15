$(document).ready(function() {

  var peelSlideInTime = 350
  var peelSlideOutTiime = 1500
  var imageFadeInTime = 500
  var imageFadeOutTime = 1500
  var sueprQuickImageFadeOutTime = 250
  var fullSizeImageFadeOutTime = 3500

  $("#pageflip").hover(function() {
    $("#pageflip #peel-image").stop()
      .animate({
        width: "200px",
        height: "200px"
      }, peelSlideInTime)
    $("#back-img").stop()
      .animate({
        width: "200px",
        height: "192px"
      }, peelSlideInTime)
  }, function() {
    $("#pageflip #peel-image").stop()
      .animate({
        width: "60px",
        height: "62px"
      }, peelSlideOutTiime)
    $("#back-img").stop()
      .animate({
        width: "60px",
        height: "60px"
      }, peelSlideOutTiime)
  })

  $(".cross").click(function(event) {

    event.preventDefault()

    $(".full-size-container").stop()
      .animate({
        opacity: "0"
      }, fullSizeImageFadeOutTime)

    $("#banner-container img").stop()
      .animate({
        opacity: "1"
      }, imageFadeInTime)
    $("#pageflip").addClass("ninja");
    $(".peel-header").addClass("fat");

    setTimeout(function() {
      $(".full-size-container").removeClass("not-ninja");
      $(".full-size-container").addClass("ninja");
      $(".full-size-container").removeClass("flex");
    }, fullSizeImageFadeOutTime)
  })

  $("#pageflip").click(function() {
    /* UI STUFF */
    $(".full-size-container").removeClass("ninja");
    $(".full-size-container").addClass("not-ninja");
    $(".full-size-container").addClass("flex");
    $(".full-size-container").stop()
      .animate({
        opacity: "1"
      }, imageFadeInTime)

    $("#pageflip").stop()
      .animate({
        opacity: "0"
      }, sueprQuickImageFadeOutTime)
  })
})
