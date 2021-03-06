# version 0.0.6 (2021-04-20)

- Unneded custom templates removed.
- Syntax improvements and de-customizations in many templates.
- More flexible subscription info in thedaily.Subscription model.
- User disabled flow changed and improved using a more friendly strategy.

# version 0.0.5 (2021-03-26)

- Dropped jquery_lazyload and using native browser load-lazy support.
- Signup support for emails upto 75 chars long (WARNING: after signup behaviour is not tested yet, may need work).
- Removed legacy customizations in ad_tag template.
- Removed share links customizations in article detail template, twitter share now uses a new Publication field.
- UX Improvements and fixes in many templates.

# version 0.0.4 (2021-03-03)

- Improvements and fixes on Category newsletters feature.
- Fixes and de-customizations for "help" and "contact" links in many templates.
- Fixes in article embed images template.

# version 0.0.3 (2021-02-17)

- tagging_autocomplete_taggit app moved to pip dependency and fixed in admin.
- Fixes to "lista de lectura" feature.
- Many improvements on article templates including also a "share" button to copy the article URL.

# version 0.0.2 (2021-01-28)

- Removed not used "inplace edit" app and related code.
- Removed not used debug app.
- Removed custom "Elegí informarte" app.
- jQuery upgraded to latest version.
- actstream, favit, ratings and updown apps moved from repo to pip dependencies.
- debug_toolbar app moved to "dev" pip dependecy.
- Removed many not used templates.
- Removed many not used tables and fields from "core" app.
- "Lista de lectura" feature. The usage of this feature is explained in https://ayuda.ladiaria.com.uy/que-es-la-lista-de-lectura/ (Spanish; la diaria's website uses utopia-cms).

# version 0.0.1 (2021-01-28)

- Initial version with the basic features.
