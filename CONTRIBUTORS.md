# Contributing to Utopia

Thank you for your interest in contributing to Utopia! Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

## To Report a Bug or New Feature

Open a new issue in [Github](https://github.com/ladiaria/utopia-cms/issues/new/choose).

## To Contribute Code or Documentation

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)

If you need to create model migrations, please consider make the migrations this way:

 - Create a `local_migration_settings.py` module using the sample file provided.
 - Run `./manage.py makemigrations --settings=migration_settings <apps>`
   (try to include in the "apps" argument only those apps whose "models.py" was modified.)

3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
