# Generated by Django 4.1.4 on 2023-08-03 12:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import martor.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('videologue', '0002_alter_video_byline_alter_video_caption_and_more'),
        ('audiologue', '0002_alter_audio_file'),
        ('core', '0030_auto_20221204_2346'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='newsletter_new_pill',
            field=models.BooleanField(default=False, verbose_name='pill de "nuevo" para la newsletter en el perfil de usuario'),
        ),
        migrations.AddField(
            model_name='publication',
            name='newsletter_new_pill',
            field=models.BooleanField(default=False, verbose_name='pill de "nuevo" para la newsletter en el perfil de usuario'),
        ),
        migrations.AlterField(
            model_name='article',
            name='audio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='articles_%(app_label)s', to='audiologue.audio', verbose_name='audio'),
        ),
        migrations.AlterField(
            model_name='article',
            name='body',
            field=martor.models.MartorField(verbose_name='cuerpo'),
        ),
        migrations.AlterField(
            model_name='article',
            name='byline',
            field=models.ManyToManyField(blank=True, related_name='articles_%(app_label)s', to='core.journalist', verbose_name='autor/es'),
        ),
        migrations.AlterField(
            model_name='article',
            name='created_by',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='created_articles_%(app_label)s', to=settings.AUTH_USER_MODEL, verbose_name='creado por'),
        ),
        migrations.AlterField(
            model_name='article',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='articles_%(app_label)s', to='core.location', verbose_name='ubicación'),
        ),
        migrations.AlterField(
            model_name='article',
            name='publication',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='articles_%(app_label)s', to='core.publication', verbose_name='publicación'),
        ),
        migrations.AlterField(
            model_name='article',
            name='sections',
            field=models.ManyToManyField(related_name='articles_%(app_label)s', through='core.ArticleRel', to='core.section', verbose_name='sección'),
        ),
        migrations.AlterField(
            model_name='article',
            name='video',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='articles_%(app_label)s', to='videologue.video', verbose_name='video'),
        ),
        migrations.AlterField(
            model_name='article',
            name='viewed_by',
            field=models.ManyToManyField(blank=True, editable=False, related_name='viewed_articles_%(app_label)s', through='core.ArticleViewedBy', to=settings.AUTH_USER_MODEL, verbose_name='visto por'),
        ),
        migrations.AlterField(
            model_name='categoryhomearticle',
            name='article',
            field=models.ForeignKey(limit_choices_to={'is_published': True}, on_delete=django.db.models.deletion.CASCADE, related_name='home_articles', to='core.article', verbose_name='artículo'),
        ),
        migrations.AlterField(
            model_name='categorynewsletterarticle',
            name='article',
            field=models.ForeignKey(limit_choices_to={'is_published': True}, on_delete=django.db.models.deletion.CASCADE, related_name='newsletter_articles', to='core.article', verbose_name='artículo'),
        ),
        migrations.AlterField(
            model_name='edition',
            name='publication',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s', to='core.publication', verbose_name='publicación'),
        ),
        migrations.AlterField(
            model_name='supplement',
            name='name',
            field=models.CharField(choices=[], max_length=2, verbose_name='nombre'),
        ),
    ]
