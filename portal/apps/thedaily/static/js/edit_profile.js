// open modal handler
function edit_profile_open_modal(){
  document.getElementById("edit_profile_modal").style.display = "flex";
  document.querySelector('html').style.overflow = "hidden";
}

$(function() {

  $('.scrollspy').scrollSpy();
  const mainHeight = $('#main-content').height();
  const tableHeight = $('.table-of-contents').height();
  const bottomOffset = mainHeight - tableHeight;

  $('.table-of-contents').pushpin({
    offset: 75,
    top: 320,
    bottom: bottomOffset,
    scrollOffset: 0
  });

  setTimeout(() => {
    if (document.querySelector(".alert.alert-success.ld-message")) {
      document.querySelector(".alert.alert-success.ld-message").style.display = "none";
    }
  }, 3000);

  // "normal" nl/communications events
  switch_change_events($('#newsletter-switches .switch-container,#ld-comunicaciones .switch-container'));

  // Open modal event
  document.getElementById("edit_profile_btn").addEventListener("click", function(e){
    e.stopPropagation();
    edit_profile_open_modal();
  });

  // Close modal when clicking outside
  document.getElementById("edit_profile_modal").addEventListener("click", function(e){
    document.getElementById("edit_profile_modal").style.display = "none";
    document.querySelector('html').style.overflow = "auto";
  });

  // Close modal when clicking on close button
  document.getElementById("edit_profile_modal__close_btn").addEventListener("click", function(e){
    document.getElementById("edit_profile_modal").style.display = "none";
    document.querySelector('html').style.overflow = "auto";
  });

  // Prevent modal from closing when clicking inside
  document.querySelector("#edit_profile_modal .edit_profile_modal__container").addEventListener("click", function(e) {
    e.stopPropagation();
  });

  // TODO: explain this last js code
  const subscriptionCancelBtns = document.getElementsByClassName("subscription-cancel-btn");
  for (let i = 0; i < subscriptionCancelBtns.length; i++) {
    subscriptionCancelBtns[i].style.display = "none";
  }
  if (document.getElementById("edit-subscriptions-btn")) {
    document.getElementById("edit-subscriptions-btn").addEventListener("click", function(e) {
      e.target.classList.contains("active") ? e.target.classList.remove("active") : e.target.classList.add("active");
      for (let i = 0; i < subscriptionCancelBtns.length; i++) {
        subscriptionCancelBtns[i].style.display = subscriptionCancelBtns[i].style.display === "block" ||
          !subscriptionCancelBtns[i].style.display ? "none" : "block";
      }
    });
  }

});
