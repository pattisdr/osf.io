# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-07-29 13:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0174_add_formblock_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrationformblock',
            name='question_id',
            field=models.CharField(db_index=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='registrationformblock',
            name='block_type',
            field=models.CharField(choices=[(b'page-heading', b'page-heading'), (b'section-heading', b'section-heading'), (b'subsection-heading', b'subsection-heading'), (b'input-label', b'input-label'), (b'short-text-input', b'short-text-input'), (b'long-text-input', b'long-text-input'), (b'file-input', b'file-input'), (b'contributors-input', b'contributors-input'), (b'single-select-input', b'single-select-input'), (b'multi-select-input', b'multi-select-input'), (b'select-input-option', b'select-input-option'), (b'select-input-other', b'select-input-other')], db_index=True, max_length=31),
        ),
        migrations.AlterUniqueTogether(
            name='registrationformblock',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='registrationformblock',
            name='block_id',
        ),
        migrations.RemoveField(
            model_name='registrationformblock',
            name='choices',
        ),
        migrations.RemoveField(
            model_name='registrationformblock',
            name='page',
        ),
        migrations.RemoveField(
            model_name='registrationformblock',
            name='section',
        ),
        migrations.RemoveField(
            model_name='registrationformblock',
            name='size',
        ),
    ]