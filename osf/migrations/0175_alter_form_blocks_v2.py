# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-08-07 22:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0174_add_formblock_models'),
    ]

    operations = [
        migrations.RenameField(
            model_name='registrationformblock',
            old_name='block_text',
            new_name='display_text',
        ),
        migrations.AddField(
            model_name='registrationformblock',
            name='question_id',
            field=models.CharField(db_index=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='registrationschema',
            name='description',
            field=models.TextField(blank=True, default=b''),
        ),
        migrations.AlterField(
            model_name='registrationformblock',
            name='block_type',
            field=models.CharField(choices=[(b'page-heading', b'page-heading'), (b'section-heading', b'section-heading'), (b'subsection-heading', b'subsection-heading'), (b'paragraph', b'paragraph'), (b'short-text-input', b'short-text-input'), (b'long-text-input', b'long-text-input'), (b'file-input', b'file-input'), (b'contributors-input', b'contributors-input'), (b'single-select-input', b'single-select-input'), (b'multi-select-input', b'multi-select-input'), (b'select-input-option', b'select-input-option'), (b'select-other-option', b'select-other-option')], db_index=True, max_length=31),
        ),
        migrations.AlterField(
            model_name='registrationformblock',
            name='required',
            field=models.BooleanField(default=False),
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
