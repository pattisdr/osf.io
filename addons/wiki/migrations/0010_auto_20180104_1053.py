# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-04 16:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('addons_wiki', '0009_wikipage_wiki_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wikiversion',
            name='identifier',
            field=models.IntegerField(default=1),
        ),
    ]
