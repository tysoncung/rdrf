# Generated by Django 2.1.12 on 2019-10-29 11:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0116_auto_20190820_1557'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinicaldata',
            name='metadata',
            field=models.TextField(blank=True, null=True),
        ),
    ]