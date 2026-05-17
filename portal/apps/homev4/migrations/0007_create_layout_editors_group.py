from django.db import migrations


def create_layout_editors_group(apps, schema_editor):
    # Permissions for new models are created by post_migrate signal, which runs after all
    # migrations complete. Calling create_permissions() explicitly ensures they exist now.
    from django.apps import apps as django_apps
    from django.contrib.auth.management import create_permissions
    create_permissions(django_apps.get_app_config("homev4"), verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(app_label="homev4", model="homelayout")
    permissions = Permission.objects.filter(
        content_type=content_type,
        codename__in=["view_homelayout", "change_homelayout"],
    )
    group, _ = Group.objects.get_or_create(name="Editores de portada")
    group.permissions.set(permissions)


def delete_layout_editors_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Editores de portada").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("homev4", "0006_rename_verbose_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_layout_editors_group, delete_layout_editors_group),
    ]
