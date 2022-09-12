# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-08-20 04:12
from __future__ import unicode_literals

import core.utils
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import tagging.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(blank=True, choices=[('NE', 'Noticia'), ('OP', 'Opinión'), ('PA', 'Fotografía'), ('HT', 'HTML'), ('CM', 'COMUNIDAD')], max_length=2, null=True, verbose_name='tipo')),
                ('headline', models.CharField(help_text='Se muestra en la portada y en la nota.', max_length=200, verbose_name='t\xedtulo')),
                ('keywords', models.CharField(blank=True, help_text='Se muestra encima del t\xedtulo en portada.', max_length=45, null=True, verbose_name='titul\xedn')),
                ('slug', models.SlugField(max_length=200, verbose_name='slug')),
                ('url_path', models.CharField(db_index=True, max_length=512)),
                ('deck', models.TextField(blank=True, help_text='Se muestra en la p\xe1gina de la nota debajo del t\xedtulo.', null=True, verbose_name='bajada')),
                ('lead', models.TextField(blank=True, help_text='Se muestra en la p\xe1gina de la nota debajo de la bajada.', null=True, verbose_name='copete')),
                ('body', models.TextField(verbose_name='cuerpo')),
                ('header_display', models.CharField(blank=True, choices=[('FW', 'Ancho completo'), ('BG', 'Grande')], default='BG', max_length=2, null=True, verbose_name='tipo de cabezal')),
                ('home_header_display', models.CharField(blank=True, choices=[('FW', 'Ancho completo'), ('FF', 'Medio y medio'), ('SM', 'Chico')], default='SM', max_length=2, null=True, verbose_name='tipo de cabezal cuando es portada')),
                ('home_lead', models.TextField(blank=True, help_text='Bajada de la nota en portada.', null=True, verbose_name='bajada en portada')),
                ('home_display', models.CharField(blank=True, choices=[('I', 'Imagen'), ('A', 'Audio'), ('V', 'Video')], max_length=2, null=True, verbose_name='mostrar en portada')),
                ('home_top_deck', models.TextField(blank=True, help_text='Se muestra en los destacados de la portada, en el caso de estar vaci\xf3 se muestra la bajada de la nota.', null=True, verbose_name='bajada en destacados')),
                ('only_initials', models.BooleanField(default=False, help_text='Marque esta opci\xf3n para que en la firma del art\xedculo se muestren \xfanicamente las iniciales del autor.', verbose_name='s\xf3lo iniciales')),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True, verbose_name='latitud')),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True, verbose_name='longitud')),
                ('is_published', models.BooleanField(default=True, verbose_name='publicado')),
                ('date_published', models.DateTimeField(default=django.utils.timezone.now, verbose_name='fecha de publicaci\xf3n')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creaci\xf3n')),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='\xfaltima actualizaci\xf3n')),
                ('views', models.PositiveIntegerField(db_index=True, default=0, verbose_name='vistas')),
                ('allow_comments', models.BooleanField(default=False, verbose_name='Habilitar comentarios')),
                ('tags', tagging.fields.TagField(blank=True, max_length=255, null=True, verbose_name='etiquetas')),
                ('allow_related', models.BooleanField(db_index=True, default=True, verbose_name='mostrar en art\xedculos relacionados')),
                ('show_related_articles', models.BooleanField(default=True, verbose_name='mostrar art\xedculos relacionados dentro de este art\xedculo')),
                ('public', models.BooleanField(default=False, verbose_name='Art\xedculo libre')),
                ('newsletter_featured', models.BooleanField(default=False, verbose_name='destacado en newsletter')),
            ],
            options={
                'get_latest_by': 'date_published',
                'ordering': ('-date_published',),
                'abstract': False,
                'verbose_name_plural': 'art\xedculos',
                'verbose_name': 'art\xedculo',
            },
            bases=(models.Model, core.utils.CT),
        ),
        migrations.CreateModel(
            name='ArticleBodyImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display', models.CharField(choices=[('BG', 'Ancho regular'), ('MD', 'Ancho amplio'), ('FW', 'Ancho completo')], default='MD', max_length=2, verbose_name='display')),
            ],
            options={
                'verbose_name': 'imagen',
                'verbose_name_plural': 'imagenes',
            },
        ),
        migrations.CreateModel(
            name='ArticleExtension',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('headline', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo')),
                ('body', models.TextField(verbose_name='cuerpo')),
                ('size', models.CharField(choices=[('R', 'Regular'), ('M', 'Mediano'), ('F', 'Full')], default='R', max_length=1, verbose_name='size')),
                ('background_color', models.CharField(blank=True, default='#eaeaea', max_length=7, null=True, verbose_name='background color')),
            ],
            options={
                'ordering': ('article', 'headline'),
                'verbose_name': 'recuadro',
                'verbose_name_plural': 'recuadros',
            },
        ),
        migrations.CreateModel(
            name='ArticleRel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveSmallIntegerField(default=None, null=True, verbose_name='orden en la sección')),
                ('home_top', models.BooleanField(default=False, help_text='Marque esta opci\xf3n para que esta nota aparezca en los destacados de la edici\xf3n.', verbose_name='destacado en portada')),
                ('top_position', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='orden')),
            ],
            options={
                'ordering': ('position', '-article__date_published'),
            },
        ),
        migrations.CreateModel(
            name='ArticleUrlHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('absolute_url', models.URLField(db_index=True, max_length=500)),
            ],
        ),
        migrations.CreateModel(
            name='ArticleViewedBy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('viewed_at', models.DateTimeField(db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='BreakingNewsModule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_published', models.BooleanField(default=False, verbose_name='publicado')),
                ('headline', models.CharField(max_length=100, verbose_name='t\xedtulo')),
                ('deck', models.CharField(blank=True, max_length=255, null=True, verbose_name='bajada')),
                ('enable_notification', models.BooleanField(default=False, verbose_name='mostrar notificaci\xf3n de alerta')),
                ('notification_url', models.URLField(blank=True, null=True, verbose_name='URL destino de la notificaci\xf3n')),
                ('notification_text', models.CharField(blank=True, max_length=255, null=True, verbose_name='texto de la notificaci\xf3n')),
                ('embeds_headline', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo de los incrustados')),
                ('embeds_description', models.CharField(blank=True, max_length=255, null=True, verbose_name='descripci\xf3n de los incrustados')),
                ('embed1_title', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo de incrustado 1')),
                ('embed1_content', models.TextField(blank=True, null=True, verbose_name='contenido de incrustado 1')),
                ('embed2_title', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo de incrustado 2')),
                ('embed2_content', models.TextField(blank=True, null=True, verbose_name='contenido de incrustado 2')),
                ('embed3_title', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo de incrustado 3')),
                ('embed3_content', models.TextField(blank=True, null=True, verbose_name='contenido de incrustado 3')),
                ('embed4_title', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo de incrustado 4')),
                ('embed4_content', models.TextField(blank=True, null=True, verbose_name='contenido de incrustado 4')),
                ('embed5_title', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo de incrustado 5')),
                ('embed5_content', models.TextField(blank=True, null=True, verbose_name='contenido de incrustado 5')),
                ('embed6_title', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo de incrustado 6')),
                ('embed6_content', models.TextField(blank=True, null=True, verbose_name='contenido de incrustado 6')),
                ('embed7_title', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo de incrustado 7')),
                ('embed7_content', models.TextField(blank=True, null=True, verbose_name='contenido de incrustado 7')),
                ('embed8_title', models.CharField(blank=True, max_length=100, null=True, verbose_name='t\xedtulo de incrustado 8')),
                ('embed8_content', models.TextField(blank=True, null=True, verbose_name='contenido de incrustado 8')),
            ],
            options={
                'verbose_name': 'm\xf3dulo de \xfaltimo momento',
                'verbose_name_plural': 'm\xf3dulos de \xfaltimo momento',
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=16, unique=True, verbose_name='nombre')),
                ('slug', models.CharField(blank=True, max_length=16, null=True, verbose_name='slug')),
                ('description', models.TextField(blank=True, null=True, verbose_name='descripci\xf3n')),
                ('order', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='orden')),
                ('has_newsletter', models.BooleanField(default=False, verbose_name='tiene NL')),
                ('title', models.CharField(blank=True, max_length=50, null=True, verbose_name='t\xedtulo en el componente de portada')),
                ('more_link_title', models.CharField(blank=True, max_length=50, null=True, verbose_name='texto en el link "m\xe1s" del componente de portada')),
                ('new_pill', models.BooleanField(default=False, verbose_name='pill de "nuevo" en el componente de portada')),
                ('full_width_cover_image_title', models.CharField(blank=True, help_text='Se muestra s\xf3lo si la foto est\xe1 seteada. (M\xe1x 50 caract.)', max_length=50, null=True, verbose_name='t\xedtulo para foto full')),
                ('full_width_cover_image_lead', models.TextField(blank=True, help_text='Se muestra s\xf3lo si la foto y el t\xedtulo est\xe1n seteados.', null=True, verbose_name='bajada para foto full')),
            ],
            options={
                'ordering': ('order', 'name'),
                'verbose_name': '\xe1rea',
            },
        ),
        migrations.CreateModel(
            name='Edition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdf', models.FileField(blank=True, help_text='<strong>AVISO:</strong> Si es mayor a 8MB probablemente no se pueda enviar por mail.', max_length=150, null=True, upload_to=core.utils.get_pdf_pdf_upload_to, verbose_name='archivo PDF')),
                ('pdf_md5', models.CharField(editable=False, max_length=32, verbose_name='checksum')),
                ('content', models.TextField(verbose_name='contenido')),
                ('downloads', models.PositiveIntegerField(default=0, verbose_name='descargas')),
                ('cover', models.ImageField(blank=True, null=True, upload_to=core.utils.get_pdf_cover_upload_to, verbose_name='tapa')),
                ('date_published', models.DateField(default=django.utils.timezone.now, verbose_name='fecha de publicaci\xf3n')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creaci\xf3n')),
                ('title', models.TextField(null=True, verbose_name='t\xedtulo')),
            ],
            options={
                'get_latest_by': 'date_published',
                'ordering': ('-date_published',),
                'abstract': False,
                'verbose_name_plural': 'ediciones',
                'verbose_name': 'edici\xf3n',
            },
        ),
        migrations.CreateModel(
            name='Home',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fixed', models.BooleanField(default=False, verbose_name='fijo')),
            ],
            options={
                'ordering': ('category',),
                'verbose_name': 'portada de \xe1rea',
                'verbose_name_plural': 'portadas de \xe1rea',
            },
        ),
        migrations.CreateModel(
            name='Journalist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='nombre')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='correo electr\xf3nico')),
                ('slug', models.SlugField(unique=True, verbose_name='slug')),
                ('image', models.ImageField(blank=True, null=True, upload_to='journalist', verbose_name='imagen')),
                ('job', models.CharField(choices=[('PE', 'Periodista'), ('CO', 'Columnista')], default='PE', help_text='Rol en que se desempe\xf1a principalmente.', max_length=2, verbose_name='trabajo')),
                ('bio', models.TextField(blank=True, help_text='Bio aprox 200 caracteres.', null=True, verbose_name='bio')),
                ('fb', models.CharField(blank=True, max_length=255, null=True, verbose_name='facebook')),
                ('tt', models.CharField(blank=True, max_length=255, null=True, verbose_name='twitter')),
                ('gp', models.CharField(blank=True, max_length=255, null=True, verbose_name='google plus')),
                ('ig', models.CharField(blank=True, max_length=255, null=True, verbose_name='instangram')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'periodista',
                'verbose_name_plural': 'periodistas',
            },
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.CharField(max_length=50, verbose_name='ciudad')),
                ('country', models.CharField(max_length=50, verbose_name='pa\xeds')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creaci\xf3n')),
            ],
            options={
                'get_latest_by': 'date_created',
                'ordering': ('country', 'city'),
                'verbose_name_plural': 'ubicaciones',
                'verbose_name': 'ubicaci\xf3n',
            },
        ),
        migrations.CreateModel(
            name='Module',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('article_1_fixed', models.BooleanField(default=False, verbose_name='fijo')),
                ('article_2_fixed', models.BooleanField(default=False, verbose_name='fijo')),
                ('article_3_fixed', models.BooleanField(default=False, verbose_name='fijo')),
                ('article_4_fixed', models.BooleanField(default=False, verbose_name='fijo')),
                ('article_5_fixed', models.BooleanField(default=False, verbose_name='fijo')),
                ('article_6_fixed', models.BooleanField(default=False, verbose_name='fijo')),
                ('article_7_fixed', models.BooleanField(default=False, verbose_name='fijo')),
                ('article_8_fixed', models.BooleanField(default=False, verbose_name='fijo')),
                ('article_9_fixed', models.BooleanField(default=False, verbose_name='fijo')),
            ],
            options={
                'ordering': ('home',),
                'verbose_name': 'destacados de \xe1rea',
            },
        ),
        migrations.CreateModel(
            name='PortableDocumentFormatPage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('number', models.PositiveSmallIntegerField(verbose_name='p\xe1gina')),
                ('pdf', models.FileField(upload_to=core.utils.get_pdfpage_pdf_upload_to, verbose_name='archivo pdf')),
                ('snapshot', models.FileField(upload_to=core.utils.get_pdfpage_snapshot_upload_to, verbose_name='captura')),
                ('content', models.TextField(verbose_name='contenido')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creaci\xf3n')),
            ],
            options={
                'get_latest_by': 'date_created',
                'ordering': ('content_type', 'object_id', 'number'),
                'verbose_name_plural': 'p\xe1ginas de PDF',
                'verbose_name': 'p\xe1gina de PDF',
            },
        ),
        migrations.CreateModel(
            name='PortableDocumentFormatPageImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=core.utils.get_pdfpageimage_file_upload_to, verbose_name='archivo')),
                ('number', models.PositiveSmallIntegerField(default=1, verbose_name='n\xfamero')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creaci\xf3n')),
            ],
            options={
                'ordering': ('-date_created', 'page', 'number', 'id'),
                'get_latest_by': 'date_created',
                'verbose_name': 'imagen de PDF',
                'verbose_name_plural': 'im\xe1genes de PDF',
            },
        ),
        migrations.CreateModel(
            name='PrintOnlyArticle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('headline', models.CharField(max_length=100, verbose_name='t\xedtulo')),
                ('deck', models.CharField(blank=True, max_length=255, null=True, verbose_name='bajada')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creaci\xf3n')),
            ],
            options={
                'get_latest_by': 'date_created',
                'ordering': ('id',),
                'verbose_name_plural': 'art\xedculos impresos',
                'verbose_name': 'art\xedculo impreso',
            },
        ),
        migrations.CreateModel(
            name='Publication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='nombre')),
                ('description', models.TextField(blank=True, help_text='Se muestra en el componente de portada.', null=True, verbose_name='descripci\xf3n')),
                ('slug', models.SlugField(unique=True, verbose_name='slug')),
                ('headline', models.CharField(max_length=100, verbose_name='title / Asunto de newsletter (NL)')),
                ('weight', models.PositiveSmallIntegerField(default=0, verbose_name='orden')),
                ('public', models.BooleanField(default=True, verbose_name='p\xfablico')),
                ('has_newsletter', models.BooleanField(default=False, verbose_name='tiene NL')),
                ('newsletter_header_color', models.CharField(default='#262626', max_length=7, verbose_name='color de cabezal para NL')),
                ('newsletter_campaign', models.CharField(blank=True, max_length=64, null=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to=b'publications', verbose_name='logo / Logo para NL')),
                ('is_emergente', models.BooleanField(default=False, verbose_name='es emergente')),
            ],
            options={
                'ordering': ['weight'],
                'verbose_name': 'publicaci\xf3n',
                'verbose_name_plural': 'publicaciones',
            },
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='nombre')),
                ('name_in_category_menu', models.CharField(blank=True, max_length=50, null=True, verbose_name='nombre en el men\xfa del \xe1rea')),
                ('slug', models.SlugField(unique=True, verbose_name='slug')),
                ('description', models.TextField(blank=True, null=True, verbose_name='descripci\xf3n')),
                ('contact', models.EmailField(blank=True, max_length=254, null=True, verbose_name='correo electr\xf3nico')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creaci\xf3n')),
                ('home_order', models.PositiveSmallIntegerField(default=0, verbose_name='orden en portada')),
                ('in_home', models.BooleanField(default=False, help_text='si el componente de portadas de esta categor\xeda est\xe1 insertado, esta opci\xf3n lo muestra u oculta.', verbose_name='en portada')),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='section_images', verbose_name='imagen o ilustraci\xf3n')),
                ('home_block_all_pubs', models.BooleanField(default=True, help_text='Marque esta opci\xf3n para mostrar art\xedculos de todas las publicaciones en los m\xf3dulos de portada.', verbose_name='usar todas las publicaciones en m\xf3dulos de portada')),
                ('home_block_show_featured', models.BooleanField(default=True, help_text='Marque esta opci\xf3n para mostrar art\xedculos destacados en los m\xf3dulos de portada.', verbose_name='mostrar art\xedculos destacados en m\xf3dulos de portada')),
                ('background_color', models.CharField(default='#ffffff', max_length=7, verbose_name='background color')),
                ('white_text', models.BooleanField(default=False, verbose_name='texto blanco')),
                ('show_description', models.BooleanField(default=False, verbose_name='mostrar descripci\xf3n')),
                ('show_image', models.BooleanField(default=False, verbose_name='mostrar imagen')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Category', verbose_name='\xe1rea')),
                ('publications', models.ManyToManyField(blank=True, null=True, to='core.Publication', verbose_name='publicaciones')),
            ],
            options={
                'ordering': ('home_order', 'name', 'date_created'),
                'get_latest_by': 'date_created',
                'verbose_name': 'secci\xf3n',
                'verbose_name_plural': 'secciones',
            },
        ),
        migrations.CreateModel(
            name='Supplement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdf', models.FileField(blank=True, help_text='<strong>AVISO:</strong> Si es mayor a 8MB probablemente no se pueda enviar por mail.', max_length=150, null=True, upload_to=core.utils.get_pdf_pdf_upload_to, verbose_name='archivo PDF')),
                ('pdf_md5', models.CharField(editable=False, max_length=32, verbose_name='checksum')),
                ('content', models.TextField(verbose_name='contenido')),
                ('downloads', models.PositiveIntegerField(default=0, verbose_name='descargas')),
                ('cover', models.ImageField(blank=True, null=True, upload_to=core.utils.get_pdf_cover_upload_to, verbose_name='tapa')),
                ('date_published', models.DateField(default=django.utils.timezone.now, verbose_name='fecha de publicaci\xf3n')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creaci\xf3n')),
                ('name', models.CharField(max_length=2, verbose_name='nombre')),
                ('slug', models.SlugField(unique=True, verbose_name='slug')),
                ('headline', models.CharField(max_length=100, verbose_name='titular')),
                ('public', models.BooleanField(default=True, verbose_name='p\xfablico')),
                ('edition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='supplements', to='core.Edition', verbose_name='edici\xf3n')),
            ],
            options={
                'get_latest_by': 'date_published',
                'ordering': ('-date_published', 'name'),
                'verbose_name_plural': 'suplementos',
                'verbose_name': 'suplemento',
            },
        ),
    ]
