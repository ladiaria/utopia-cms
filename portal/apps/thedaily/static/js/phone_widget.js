function phone_widget(local_country, util_script, required=false, no_placeholder=false) {

  const input = document.querySelector("#id_phone");
  let options = {
    initialCountry: local_country,
    hiddenInput: function(phone) {
      return {
        phone: "phone"
      };
    },
    utilsScript: util_script
  };
  if (no_placeholder) {
    options.placeholderNumberType = false;
  }
  const iti = window.intlTelInput(input, options);
  input.addEventListener("countrychange", function(e) {
    e.target.value = "";
  });
  input.addEventListener("keyup", function(e) {
    let val = iti.getNumber();
    input.setCustomValidity(required && !val || val && !iti.isValidNumber() ? "Formato incorrecto" : "");
  });

}
