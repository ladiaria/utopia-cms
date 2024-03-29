# Generated by Django 4.1.4 on 2023-08-28 00:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cartelera', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archivedevent',
            name='access_type',
            field=models.CharField(choices=[('f', 'Gratuito'), ('s', 'Para suscripciones pagas')], default='s', max_length=1, verbose_name='acceso al evento'),
        ),
        migrations.AlterField(
            model_name='categoriaevento',
            name='nombre',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='nombre'),
        ),
        migrations.AlterField(
            model_name='cine',
            name='address',
            field=models.TextField(blank=True, null=True, verbose_name='dirección'),
        ),
        migrations.AlterField(
            model_name='cine',
            name='nombre',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='nombre'),
        ),
        migrations.AlterField(
            model_name='cine',
            name='phones',
            field=models.CharField(max_length=250, verbose_name='telefonos'),
        ),
        migrations.AlterField(
            model_name='eventobase',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='descripción'),
        ),
        migrations.AlterField(
            model_name='eventobase',
            name='end',
            field=models.DateTimeField(verbose_name='fin'),
        ),
        migrations.AlterField(
            model_name='eventobase',
            name='poster',
            field=models.ImageField(blank=True, null=True, upload_to='cartelera/posters'),
        ),
        migrations.AlterField(
            model_name='eventobase',
            name='precio',
            field=models.CharField(max_length=250, verbose_name='precio'),
        ),
        migrations.AlterField(
            model_name='eventobase',
            name='start',
            field=models.DateTimeField(verbose_name='comienzo'),
        ),
        migrations.AlterField(
            model_name='eventobase',
            name='title',
            field=models.CharField(max_length=250, verbose_name='titulo'),
        ),
        migrations.AlterField(
            model_name='liveembedevent',
            name='access_type',
            field=models.CharField(choices=[('f', 'Gratuito'), ('s', 'Para suscripciones pagas')], default='s', max_length=1, verbose_name='acceso al evento'),
        ),
        migrations.AlterField(
            model_name='obraenteatro',
            name='horarios',
            field=models.TextField(blank=True, null=True, verbose_name='horarios'),
        ),
        migrations.AlterField(
            model_name='peliculaencine',
            name='horarios',
            field=models.TextField(blank=True, null=True, verbose_name='horarios'),
        ),
        migrations.AlterField(
            model_name='teatro',
            name='address',
            field=models.TextField(blank=True, null=True, verbose_name='dirección'),
        ),
        migrations.AlterField(
            model_name='teatro',
            name='nombre',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='nombre'),
        ),
        migrations.AlterField(
            model_name='teatro',
            name='phones',
            field=models.CharField(max_length=250, verbose_name='telefonos'),
        ),
    ]
