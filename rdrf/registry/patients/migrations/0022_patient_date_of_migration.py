# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-21 11:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0021_auto_20170220_1537'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='date_of_migration',
            field=models.DateField(blank=True, null=True),
        ),
    ]