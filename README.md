<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![BSD 3-Clause "New" or "Revised" License][license-shield]][license-url]



<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/ladiaria/utopia-cms">
    <img src="static/img/logo-utopia.png" alt="Logo" height="80">
  </a>

  <h3 align="center">Utopía CMS</h3>

  <p align="center">
    <em>Content Management System</em> tool that different teams in a newsroom can use to manage content.
  </p>
</p>



<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

![Front-end Screen Shot][product-screenshot1]

### Subscriptions

Allows creation of print and digital subscriptions, add different payment methods, collect statistics and maintain relationships with readers.

![Back-end Screen Shot][product-screenshot2]

### Paywall

Paywall is a way to control access to content and encourage subscriptions.

### SEO

Website optimized to be search engine friendly. Features like semantic headings, structured data (Schema and Open Graph), tags, AMP, accessibility, performance, and more.

### Community

Spaces for interaction between readers can be created in order to empower connections, so that the community of people who support your project is part of it.

### Reliable

Built on modern and popular languages like Python and the Django framework.

### Modular

It allows you to choose which features to use depending on the needs of your newsroom; also contains integrations with other open source tools and platforms such as Discourse, Coral and Chatwoot.

### Why choose Utopía

Utopía offers a technological package that sustains the media practice by paid subscriptions or memberships, a content management model supported by an open knowledge community, tools for moderating participation of the audience, with the purpose of co-creating journalism  with the community.

### A project by la diaria

From la diaria we want to share with other media organizations our management experience and the tools developed with the help of our technical team. We expect to do so by releasing the project as free software with the goal of collaborating with other media companies and co-creating new solutions.

We are sharing 15 years of experience in managing a media cooperative, which is close to being 100% supported by our community.

### Supported by Google

Utopía was one of the selected projects by Google News Initiative in Latin America to receive support from the Innovation Challenge Fund.

### Built With

* [Django](https://djangoproject.com/)


<!-- GETTING STARTED -->
## Getting Started

This is an example of how you may give instructions on setting up your project locally.
To get a local copy up and running follow these simple example steps.

### Prerequisites

- Virtualenv for Python2.7: https://virtualenv.pypa.io/en/latest/

- System packages, names can vary by OS/distribution:

  mariadb nginx libtiff libtiff-devel giflib giflib-devel python-pillow MySQL-python python-dateutil python-vobject python-oauth2 pyPdf python-openid pytz pycrypto python-memcached python-requests-oauthlib python-requests rubygem-sass npm gcc libmaxminddb-devel

- npm (Node.js packages):

  postcss-cli autoprefixer

### Local installation for development in Linux or Mac (Devs / DevOps)

#### Local repository and virtualenv configuration

- Clone the project repository to any local destination directory and init its git submodules:

  `user@host:~ $ git clone -b main https://github.com/ladiaria/utopia-cms && cd utopia-cms && git submodule update --init`

- Clone also another repo with more static files needed:

  `user@host:~/utopia-cms $ git clone -b main https://github.com/ladiaria/lightGallery static/lightGallery`

- Create a virtualenv (venv) for Python2.7 using system-site-packages (the subdirectory `~/.virtualenvs` is not needed, we use it in this guide because is the default virtualenv directory in the tool [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/), also the virtual environment name can be any other, "utopiacms" is choosed in this guide):

  `user@host:~/utopia-cms $ mkdir -p ~/.virtualenvs && virtualenv2 --system-site-packages ~/.virtualenvs/utopiacms`

- Activate the new virtual environment and install the required Python modules:

  ```
  user@host:~/utopia-cms $ source ~/.virtualenvs/utopiacms/bin/activate
  (utopiacms) user@host:~/utopia-cms $ pip install -r portal/requirements.txt
  ```

#### Database setup

- Create a new database and grant user privileges to a new or existing database user:

```
(utopiacms) user@host:~/utopia-cms $ sudo mysqladmin create utopiacms
(utopiacms) user@host:~/utopia-cms $ sudo mysql
MariaDB [(none)]> CREATE USER 'utopiacms_user'@'localhost' IDENTIFIED BY 'password';
MariaDB [(none)]> GRANT ALL PRIVILEGES ON utopiacms.* TO 'utopiacms_user'@'localhost';
```

- Create a local settings module based on the sample given and edit the file created with your database settings created above and also fill the `SECRET_KEY` variable using any string or a more secure one generated for example with [this web tool](https://djecrety.ir/).

```
(utopiacms) user@host:~/utopia-cms $ cd portal
(utopiacms) user@host:~/utopia-cms/portal $ cp local_settings_sample.py local_settings.py
(utopiacms) user@host:~/utopia-cms/portal $ vim portal/local_settings.py
```

- Create needed tables using Django's `syncdb` management command:

`(utopiacms) user@host:~/utopia-cms/portal $ python -W ignore manage.py syncdb --noinput`

- Create `social_django` module tables using Django's `sqlall` management command piped to the database (provide the correct database user and password created before):

`(utopiacms) user@host:~/utopia-cms/portal $ python -W ignore manage.py sqlall social_django | mysql -u utopiacms_user -p utopiacms`

- Run the migration script provided, it will create all the rest of database tables needed:

`(utopiacms) user@host:~/utopia-cms/portal $ libs/scripts/migrate.sh`

#### Development environment setup

- Create a Django superuser and collect static files using this commands:

```
(utopiacms) user@host:~/utopia-cms/portal $ python -W ignore manage.py createsuperuser
(utopiacms) user@host:~/utopia-cms/portal $ python -W ignore manage.py collectstatic --noinput
```

- Configure Nginx for reverse proxying the Django's development server and start it:

```
(utopiacms) user@host:~/utopia-cms/portal $ sudo cp ../docs/nginx_example_conf/utopia-cms-dev.conf /etc/nginx/conf.d
(utopiacms) user@host:~/utopia-cms/portal $ sudo systemctl restart nginx
(utopiacms) user@host:~/utopia-cms/portal $ python -W ignore manage.py runserver hexxie.com:8000
```

- Login with superuser created before, edit the default site domain and create a publication with the same slug to the one configured in `settings.DEFAULT_PUB`:

Point your preferred web browser to https://hexxie.com/admin/sites/site/1/ and you will be redirected to the Django's admin site login page, after login you will be redirected again to the default site change form, change its domain to `hexxie.com` and optionally also change its display name to any name you want, save the changes and then go to https://hexxie.com/admin/core/publication/add/ fill the form to create the new publication, save it and then you will be able to see the home page working at https://hexxie.com/.


### Deployment (DevOps / SysAdmins)

TODO: describe steps using nginx + uwsgi

<!-- USAGE EXAMPLES -->
## Usage

TODO: explain some important settings like the "contact url" and also how to catch non-defined urls like "/ayuda"

<!-- ROADMAP -->
## Roadmap

TODO: describe the improvements that we will be doing after this first release and also the ones we plan for the
second release.

See the [open issues](https://github.com/ladiaria/ladiaria-cms/issues) for a list of proposed features (and known issues).


<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- LICENSE -->
## License

Distributed under the BSD 3-Clause "New" or "Revised" License. See `LICENSE.txt` for more information.



<!-- CONTACT -->
## Contact

la diaria - [@ladiaria](https://twitter.com/ladiaria)

Project Link: [https://github.com/ladiaria/utopia-cms](https://github.com/ladiaria/utopia-cms)



<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/ladiaria/utopia-cms.svg?style=for-the-badge
[contributors-url]: https://github.com/ladiaria/ladiaria-cms/blob/main/CONTRIBUTORS.md
[forks-shield]: https://img.shields.io/github/forks/ladiaria/utopia-cms.svg?style=for-the-badge
[forks-url]: https://github.com/ladiaria/utopia-cms/network/members
[stars-shield]: https://img.shields.io/github/stars/ladiaria/utopia-cms.svg?style=for-the-badge
[stars-url]: https://github.com/ladiaria/utopia-cms/stargazers
[issues-shield]: https://img.shields.io/github/issues/ladiaria/utopia-cms.svg?style=for-the-badge
[issues-url]: https://github.com/ladiaria/utopia-cms/issues
[license-shield]: https://img.shields.io/github/license/ladiaria/utopia-cms.svg?style=for-the-badge
[license-url]: https://github.com/ladiaria/utopia-cms/blob/main/LICENSE.txt
[product-screenshot1]: docs/images/screenshot1.png
[product-screenshot2]: docs/images/screenshot2.png
