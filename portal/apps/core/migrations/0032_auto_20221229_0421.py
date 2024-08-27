# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-12-29 04:21

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_category_newsletter_new_pill_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleCollection',
            fields=[
                ('article_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.Article')),
                ('traversal_categorization', models.BooleanField(default=False, help_text='Si está marcada, prioriza la categorización de la colección para todo el contenido de la colección', verbose_name='categorización transversal')),
            ],
            options={
                'verbose_name': 'colección',
                'verbose_name_plural': 'colecciones',
            },
            bases=('core.article',),
            managers=[
                ('published', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='ArticleCollectionRelated',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveSmallIntegerField(default=None, null=True, verbose_name='orden en la colección')),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Article', verbose_name='artículo')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='linked_articles', to='core.ArticleCollection')),
            ],
            options={
                'verbose_name': 'artículo vinculado',
                'verbose_name_plural': 'artículos vinculados',
                'ordering': ('position', '-article__date_published'),
            },
        ),
        migrations.AddField(
            model_name='articlecollection',
            name='related_articles',
            field=models.ManyToManyField(related_name='linked_collections', through='core.ArticleCollectionRelated', to='core.Article'),
        ),
        migrations.AlterUniqueTogether(
            name='articlecollectionrelated',
            unique_together=set([('collection', 'article')]),
        ),
    ]
