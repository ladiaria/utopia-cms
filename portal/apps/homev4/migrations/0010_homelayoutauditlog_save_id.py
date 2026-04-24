import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("homev4", "0009_homelayoutauditlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="homelayoutauditlog",
            name="save_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, verbose_name="ID de guardado"),
            preserve_default=False,
        ),
    ]
