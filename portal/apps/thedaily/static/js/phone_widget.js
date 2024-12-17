function phone_widget(
  local_country, intl_tel_input_cdn, local_lang, required=false, use_placeholder=false, extra_options={}
) {

  import(intl_tel_input_cdn + "js/i18n/" + local_lang + "/index.js").then(module => {

    const { default: allTranslations } = module;
    const input = document.querySelector("#id_phone");
    if (input) {
      let options = {
        initialCountry: local_country,
        hiddenInput: function(phone) {
          return {
            phone: "phone"
          };
        },
        utilsScript: intl_tel_input_cdn + "js/utils.js",
        i18n: allTranslations,
        useFullscreenPopup: false
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

  });

}
