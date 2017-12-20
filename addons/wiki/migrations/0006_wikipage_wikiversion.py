# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-19 22:43
from __future__ import unicode_literals

import addons.wiki.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0075_merge_20171207_1511'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('addons_wiki', '0005_auto_20170713_1125'),
    ]

    operations = [
        migrations.CreateModel(
            name='WikiPage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('content_type_pk', models.PositiveIntegerField(blank=True, null=True)),
                ('page_name', models.CharField(max_length=200, validators=[addons.wiki.models.validate_page_name])),
                ('date', osf.utils.fields.NonNaiveDateTimeField(auto_now_add=True)),
                ('content', models.TextField(blank=True, default=b'')),
                ('node', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='osf.AbstractNode')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WikiVersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('wiki', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='addons_wiki.WikiPage')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
