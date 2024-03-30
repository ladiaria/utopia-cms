# Utopía CMS documentation

## About this documentation site

Starting a documentation site for this project, the main goal is to create docs here as better as possible to help anyone who wants to install or use this Django project, but also this first (an minimal) version of the documentation site was created specially to write about the next release that will support from this commit and up, the basic integration with our another main project, Utopía CRM, both using its default installations and requiering only a few steps of configuration.

So, the next section, will talk about this integration and of course, with the time, this documentation home page will include all the docs that we have now and the many others that we must to create.

## Utopía CRM integration

This is an skel of steps that we will describe better on next commits, but is a good start point to have an idea on what are the things to do to obtain a deployment of Utopía CMS that can interoperate with a deployment of Utopía CRM.

1. Install both projects, Utopía CRM and CMS, following the INSTALL.md docs in the root of each, and after having both systems up and running with admin access in front-end, and also access to modify the "local settings", continue to next step.
2. Configure the url of each one in the other:
    - In the `local_settings.py` of `utopia-crm` assign the CMS root url in the setting `LDSOCIAL_URL`, example:

        ```
        LDSOCIAL_URL = "https://yoogle.com/"
        ```

    - In the `local_settings.py` of `utopia-cms` assign the CRM API base url in the setting `CRM_API_BASE_URI`, example:

        ```
        CRM_API_BASE_URI = 'http://localhost:8000/api/'
        ```

3. On each django admin site, generate the API-Key to set in the local settings of the other project, the steps to follow are identically on each admin site, follow the [djangorestframework-api-key docs](https://florimondmanca.github.io/djangorestframework-api-key/guide/#creating-and-managing-api-keys) to obtain both keys and then assign each one using this mapping:

    - The key generated in the CMS must be set in the `LDSOCIAL_API_KEY` variable of the CRM `local_settings.py` file, example:

        ```
        LDSOCIAL_API_KEY = "aTdKvX2p.qnqGZt6DYyJ8w8o5RsS15tF3eDI6Q8W0"
        ```

    - Do the same in the other admin site and assign the new second key to the setting `CRM_UPDATE_USER_API_KEY` in the CMS `local_settings.py` file, example:

        ```
        CRM_UPDATE_USER_API_KEY = "uK9DmR4s.W3ZtF6y1nA3eD5gH7jK9mP1qRW3ZtF6y"
        ```

4. Enable the integration on each project assigning `True` to this local settings variables:
   In the CMS local_settings.py file:

    ```
    CRM_UPDATE_USER_ENABLED = True
    ```

    In the CRM local_settings.py file:

    ```
    WEB_UPDATE_USER_ENABLED = True
    ```

5. Restart both servers and test the integration creating Users in CMS matching Contacts in CRM with the same email, then for example, when email is changed in one project, the change will be also performed in the other system, take a look also in the `contact_id` field of CMS Subscribers (`thedaily.models.Subscriber.contact_id) this is the "link" metadata with more precedence used by the apis who sync any object with its respective "pair".

We hope have much more documentation in the next commits, for this topic and many others.
