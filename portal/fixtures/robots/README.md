# In this directory

Fixtures containing useful objects for the robots.txt app (the app that generates the `/robots.txt` response). At this readme update, the following fixtures are available:

- `urls_common.json`: Common url patterns in our environs, `/`, `/*`, etc.

- `rule_google_extended.json`: Google IA crawler allow rule. (Depends on `urls_common.json` and the existence of a site object with `id=1`)
