# version 0.2.4 (2022-04-17)

- Signupwall improvements and fixes.
- Robots meta tag de-customization and improvements.
- Offline support in send_category_nl command.
- Better support to load GTM and GA.
- Better default configuration.
- UX and CSS improvements.
- Requirements fix.
- More flexibility to customize the breaking news module.
- Custom users api view updates.

# version 0.2.3 (2022-03-17)

- The "Most readed" articles feature was refactored and improved.
- Fixed an error in Publication's admin when the logo image is missing from filesystem.
- Many syntax code style improvements.
- Improvements on subscription forms validations and generated email messages.
- The "materialize" Python module is not required and was removed from requirements and installed apps.
- UX and CSS improvements.

# version 0.2.2 (2022-03-05)

- Support for custom area newsletters content independent from area's home.
- UX Improvements in the admin of area homes and a related "TODO" added.

# version 0.2.1 (2022-03-02)

- Restricted publications feature (articles content are completely locked to non-subscribers).
- Additional access: A restricted -or any- article can behave as a regular one, if a publication is selected in this new article field.
- Article detail template was fixed (closing tags were missing in some situations) and was reindented properly.
- Signupwall middleware fixed keeping or spending credits in a more accurately way.
- Article slug field changed to read-only widget because edits on it are ignored.
- Article admin change form was reorganized better.
- Elastic search results sort and phrase match support.
- Area newsletters sync support with utopia-crm.
- UX and CSS improvements.
- Publications menu improvements.
- Publication's headline attribute usage support when rendering the publication's name in many templates.
- Improvements in context variables usage through template tags.
- Allow more flexibility to hide dates in article cards.
- A custom not used setting removed from a context processor.
- Not used imports removed in some modules, more flexibility in notifications template preview view with an important "TODO" added.
- Section in article cards are taken in a better way, giving a better publication precedence.
- Many syntax code style improvements.

# version 0.2.0 (2022-02-01)

- Inner sections support for category detail view.
- Custom section detail templates support by settings.
- Gruped tags new app allows grouping tags for customizations.
- CSS updates and not ascii char error fixed.
- More customization flexibility support on rendering dates in article cards.

# version 0.1.9 (2022-01-27)

- Elasticsearch support in search app.
- Many important improvements in core.models.update_category_home function.
- Allow more flexibility when using some of the custom child templates that can be configured by settings.
- Templates and template tags used to render home 'row' components were improved with minor fixes, todo's and features.
- Remove position holes after saving a CategoryHome using the admin.
- Performance improvement for audio stats in dashboard app.
- General improvements: de-customizations, syntax code style, UX, some method features using optional args.

# version 0.1.8 (2022-01-08)

- Fix one context variable value assignation between template tags rendering.
- Uniqueness added on (home, position) columns in categoryhomearticle relation.

# version 0.1.7 (2022-01-03)

- Tests documentation improvements.
- Edition headers feature.
- Improvements to display the published date in article cards.
- Support to hide the photographer in article cards.
- Many improvements, fixes and de-customizations in UX, migrations, modules and templates.
- Performance improvements in some raw SQL sentences.
- UX support to "read-later" articles from the article card.

# version 0.1.6 (2021-12-03)

- Cleaned custom values and unused fields in some migrations and models.
- Performance improvements with new database indexes and raw sql optimization.
- "defensoria" custom deprecated template tag removed.
- django-debug-toolbar usage support.

# version 0.1.5 (2021-12-02)

- Fixes in the installation guide.
- pip dependencies updates.
- Cleaned custom values and unused fields in some migrations and models.
- Improved syntax code style in many modules and templates.
- not-maintained / duplicated features commented / removed in comunidad app.
- Custom unneeded shell scripts removed.
- Ad impressions and clicks logs registered in mongodb for better mysql performance.
- "with" template tag usage syntax updated.
- Better way to partitioning the receipts in the send_category_nl management command.
- Some JavaScript loading optimizations, loaded in the pages that require them.
- Support for new blocks like category sections and articles by tag.
- Improvements in dashboard app.
- Support for a better customization of the mobile footer navbar.

# version 0.1.4 (2021-10-20)

- Support for custom subject in category newsletters.

# version 0.1.3 (2021-10-09)

- Development domain changed to yoogle.com
- defer js in base template

# version 0.1.2 (2021-10-05)

- Support to disable (default) the "promo code" field for new subscriptions.
- Fixes and improvements in the Article admin change form.

# version 0.1.1 (2021-10-02)

- Progressive Web Apps (PWA) support.
- "Keep reading" feature dropped.
- Many author customizations removed.
- UX improvements.
- Syntax formatting improvements and fixes on many modules and templates.
- Unneeded secure_static context processor removed.
- settings and test_settings modules improved eliminating not needed lines.
- Fixed edition PDF download view.
- Fixed Category.latest_articles method when the category has no home.
- Support for a non-subscriber version in the category newsletter preview feature.
- Support for direct path redirect in section redirect feature.
- Improvements in dashboard views.
- Support for custom templating in publications home pages.
- Support for custom headers in the to_response decorator.
- Unneeded formtools pip dependency removed.
- Support for a custom css for the print version.

# version 0.1.0 (2021-08-21)

- Django support upgraded to version 1.11 (dropped support for Django 1.5).
- Install guide upgraded, improved and tested.
- django-robots upgraded and removed from repo.
- typi submodule removed.
- Log usage and errror handling improved in send_category_nl command.
- Custom things like settings and some views were removed.
- Syntax formatting improvements and fixes on many modules.
- UX and CSS improvements in many templates.

# version 0.0.9 (2021-06-15)

- Support to exclude categories with order, from the top menu.

# version 0.0.8 (2021-06-15)

- Removed a custom attribute and method from Subscriber model.
- Renamed "costumer_id" (typo) attribute from Subscriber model to "contact_id".
- Changed urls and md5 imports to avoid deprecation warnings.
- Syntax formatting improvements on many modules.
- A deprecated-custom urls module was removed.
- Improvements on "Subscriptions" section of user profile template.
- Fixed a templatetag error when a publication does not exist.

# version 0.0.7 (2021-06-01)

- "home" app removed, categories' homes now are managed by new models in core.
- Generalizations for fields used by publications newsletters.
- Code style formatting improved on many modules.
- UX and CSS improvements in many templates.
- Generalizations for menu items for latest articles in sections, now can be defined in settings.
- Article detail view cache activated / deactivated automatically when signupwall is disabled / enabled.

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
