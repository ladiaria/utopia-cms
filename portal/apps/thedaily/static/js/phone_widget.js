function phone_widget(local_country, util_script, required=false, use_placeholder=false, extra_options={}) {

  const input = document.querySelector("#id_phone");
  if (input) {
    let options = {
      initialCountry: local_country,
      hiddenInput: function(phone) {
        return {
          phone: "phone"
        };
      },
      utilsScript: util_script
    };
    if (!use_placeholder) {
      options.placeholderNumberType = false;
    }
    if (extra_options) {
      Object.assign(options, extra_options);
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
}
