# Utopía CMS documentation

## About this documentation site

Starting a documentation site for this project, the main goal is to create documentation that is as good as possible to help anyone who wants to install or use this Django project, but also this first (and minimal) version of the documentation site was created specially to write about the next release that will support from this commit and up, the basic integration with our another main project, Utopía CRM, both using its default installations and requiering only a few steps of configuration.

So, the following section (Utopía CRM integration), will cover this integration and, over time, this documentation home page will include all the docs that we have now and the many others that we must create.

TODO: make separated md files for each next `##` and link them here.

### How-to build this documentation site (for this project maintainers)

Standing in a working tree, on `main` branch and in the `docs` directory (a subdirectory of the project root), with the "venv" activated, install the `mkdocs` module using `pip` (if not already installed) and run this command:

```
mkdocs gh-deploy
```

## Utopía CRM integration

This is an skel of steps that we will describe better on next commits, but is a good start point to have an idea on what are the things to do to obtain a deployment of Utopía CMS that can interoperate with a deployment of Utopía CRM.

1. Install both projects, Utopía CRM and CMS, following the INSTALL.md docs in the root of each, and after having both systems up and running with admin access in front-end, and also access to modify the "local settings", continue to next step.
2. Configure the url of each one in the other:
    - In CRM `local_settings.py` assign the CMS root url in the setting `LDSOCIAL_URL`, example:

        ```
        LDSOCIAL_URL = "https://yoogle.com/"
        ```

    - In CMS `local_settings.py` assign the CRM API base url in the setting `CRM_API_BASE_URI`, example:

        ```
        CRM_API_BASE_URI = 'http://localhost:8000/api/'
        ```

3. On each django admin site, generate the API-Key to set in the local settings of the other project, the steps to follow are identically on each admin site, follow the [djangorestframework-api-key docs](https://florimondmanca.github.io/djangorestframework-api-key/guide/#creating-and-managing-api-keys) to obtain both keys and then assign each one using this mapping:

    - The key generated in the CMS must be assigned to the `LDSOCIAL_API_KEY` variable in CRM `local_settings.py`, example:

        ```
        LDSOCIAL_API_KEY = "aTdKvX2p.qnqGZt6DYyJ8w8o5RsS15tF3eDI6Q8W0"
        ```

    - Do the same in the other admin site and assign the key to the `CRM_UPDATE_USER_API_KEY` variable in CMS `local_settings.py`, example:

        ```
        CRM_UPDATE_USER_API_KEY = "uK9DmR4s.W3ZtF6y1nA3eD5gH7jK9mP1qRW3ZtF6y"
        ```

4. Enable the integration on each project assigning `True` to this local settings variables:

    - In CMS `local_settings.py`:

        ```
        CRM_UPDATE_USER_ENABLED = True
        ```

    - In CRM `local_settings.py`:

        ```
        WEB_UPDATE_USER_ENABLED = True
        ```

5. Restart both servers and test the integration creating Users in CMS matching Contacts in CRM with the same email, then for example, when email is changed in one project, the change will be also performed in the other system, take a look also in the `contact_id` field of CMS Subscribers (`thedaily.models.Subscriber.contact_id) this is the "link" metadata with more precedence used by the apis who sync any object with its respective "pair".

We hope have much more documentation in the next commits, for this topic and many others.

## Caching using the cache backend configured in Django

### Intro

TODO: write about caching and why it is important to use it and very hard to do it right.

### Configuration

TODO: Explain why we had to write a custom middleware to handle the cache control headers, instead of only using the settings and middlewares that already exist in Django.

tl;dr: Obtain the results you want working with caching requirements is hard, and it is even harder to do it right.

#### AnonymousRequest and Response middlewares

TODO: Explain what they do.

#### Decorators

TODO: Explain what they do.

#### Home (url `/`)

Utopia-cms default cache settings are ready to cache any part of the home (url `/`), for anonymous users only and also for authenticated users changing one of those settings, Since this configuration is made relying in __Django's cache framework__ (doc linked at the end of this section), it depends on all lower level caching conditions Django's cache framework has, for example the UserAgent (mobile/desktop) and the value of the path in the request url. By default for 2 minutes, but this __max_age__ can be changed overriding the `HOMEV3_INDEX_CACHE_MAXAGE` setting.

To deploy this cache in the home, you have to generate a custom template for the default publication (TODO: write and refer documentation for this, giving a tutorial for creating and configuring an utopia-cms customization Django app) and make it work as the template being rendered when the / url is requested, the html code in this template that you want to cache, must be encapsulated around `{% cache max_age_value key_name %} ... {% endcache %}` the explanation about the `max_age_value` and `key_name` can be found in the [Django's cache framework documentation](https://docs.djangoproject.com/en/4.2/topics/cache/).

#### Any other url

The included support to cache any other url that utopia-cms can serve among with the conditions to make it work are described in the following item list:

* The url or urls you want to cache should render exactly the same result to all users, regardless of the user's authentication status, anonymous or authenticated, if not, you probably will be render missing or wrong results for at least one of this kinds of users.
* The url must be named and its name must be included in the `PORTAL_ANON_REQUEST_URL_NAMES_INCLUDE_AUTH` setting.
* The url must be handled by a view and the view must be under your control to decorate it with this two decorators:
    * `@cache_control(max_age=seconds, public=True)`
    * `@vary_on_headers("Cookie")`

When all this conditions are met, the url will be cached using the cache backend configured in Django and return the same response content for any request that matches the conditions to be cached.

This is what we can confirm that works with the current configuration, of course many other set of configurations can also work, and all the expert Django developers who are reading this words (hope one can do it someday ;) can be thinking in "why this people made such a complicated strategy instead of xyz?", as said before, cache is very hard to do it right, other "easy" strategies were also tested and they didn't work as expected, so we decided to do it the way we did.

TODO: add example of how to do it with the most-read articles block maybe is the first candidate to "fix" the cache that we believe was well configured but it wasn't.

## Newsletters

### Intro

TODO: write about what a NL is, how to preview and send

### Default content

The default content of each newsletter can be modified by redefining the template of each newsletter. Additionally, by customizing the available settings for this functionality, many combinations of alternative content can be achieved. Over the years in production, we have made it possible to meet various requirements requested by editorial, sales, management, and other teams.

* Publications:

Featured articles are selected, meaning those that would appear on the publication's cover.

* Areas:

Priority is given to the "area newsletter" object that may exist with valid dates (using the "valid until" datetime field) for the respective area. If the former is not valid or does not exist, articles from the "area cover" object associated with the respective area are then selected.

## Management commands

Like any other Django management command, these commands must be executed calling `manage.py` using the Python executable of the utopia-cms installation virtual environment.

### core.dump_articles

Dumps the Articles given by id or filter expression to a JSON file, the generated file can then be loaded using `loaddata` command.
The command will also copy all images related to the articles being dumped to the `photos` subdirectory under the dump directory that was given to the command by argument.

* positional arguments:

    * **article_ids**: Article IDs separated by space, takes precedence over `--filter-kwargs`.

* customization options:

    * **--filter-kwargs**: A dict in JSON format, it will be passed as `**kwargs` to `Article.filter()` to obtain the set to be dumped.<br>
    * **--dump-dir**: Save generated `dump.json` file and copy images to this directory.

* run `./manage.py help dump_articles` to get the complete set of options available.

#### Dump & load usage example:

1. Go to the host/environment that you want to export from and execue the command, for example, to dump all articles with an ID greater than 1000 to the directory `article_dumps` under the user's home directory, run<br>
  ```
  ./manage.py dump-articles --filter-kwargs '{"id__gt": 1000}' --dump-dir ~/article_dumps
  ```

2. Go to the environment you want to load the dump, download it and run the `loaddata` command. (the same location path will be used for this example)<br>
  ```
  ./manage.py loaddata -i ~/article_dumps/dump.json
  ```

3. If the dump directory was downloaded recursively (with the `photos` subdirectoy), you can copy the images to the target media location:<br>
  ```
  cp ~/article_dumps/photos/* media/photologue/photos
  ```

## YouTube API

Utopia CMS backend uses the Youtube Data API to offer a feature to get youtube video information and rendering, the functionality is quite basic but it might be cover many needs, since youtube API itself is quite limited and also for the purpose of this information system, video functionality rarely requires complex implementations.

### Usage

To use the Youtube API, you have to create a credentials file to use the oauth authentication or use an API key, you can follow the instructions in Youtube API official docs to achieve this requirement. We also have a [python script](videos.py) that exlpains how to obtain a credentials file and use oauth, this script was developed through many hours of trial and error. Taking a look at it may help you avoid some headaches.

## CKEditor

Under development, the plan is to use CKEditor as the main editor for the body field of articles, but for now, the martor editor will be used. Right now the support to use CKEditor overriding the target field class and setting some variables is available, documentation in that way will be added soon here.

The approach is using a completely in-repo CKeditor which must be built using npm before a collectstatic is performed. We already have this scenario working using a custom app and it will migrated as soon as possible to this open source project.
