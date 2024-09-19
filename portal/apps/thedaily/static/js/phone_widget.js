function phone_widget(local_country, util_script, required=false, extraOptions=false) {

  const input = document.querySelector("#id_phone");
  let options = {
    initialCountry: local_country,
    hiddenInput: function(phone) {
      return {
        phone: "phone"
      };
    },
    utilsScript: util_script,
  };

  if (extraOptions) Object.assign(options, extraOptions);

  const iti = window.intlTelInput(input, options);
  input.addEventListener("countrychange", function(e) {
    e.target.value = "";
  });
  input.addEventListener("keyup", function(e) {
    let val = iti.getNumber();
    input.setCustomValidity(required && !val || val && !iti.isValidNumber() ? "Formato incorrecto" : "");
  });

}
