function phone_widget(local_country, util_script, required=false) {

  const input = document.querySelector("#id_phone");
  const iti = window.intlTelInput(input, {
    initialCountry: local_country,
    hiddenInput: function(phone) {
      return {
        phone: "phone"
      };
    },
    utilsScript: util_script
  });
  input.addEventListener("countrychange", function(e) {
    e.target.value = "";
  });
  input.addEventListener("keyup", function(e) {
    let val = iti.getNumber();
    // error = (required && !val) || (!required && val && invalid)
    input.setCustomValidity(required && !val || val && !iti.isValidNumber() ? "Formato incorrecto" : "");
  });

}
