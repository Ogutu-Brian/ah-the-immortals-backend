# Generated by Django 2.2 on 2019-05-16 10:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('highlights', '0002_auto_20190516_0615'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='highlight',
            unique_together=set(),
        ),
    ]
