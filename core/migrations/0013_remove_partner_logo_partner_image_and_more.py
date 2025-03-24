# Generated by Django 5.1.1 on 2025-03-10 07:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_alter_client_phone'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='partner',
            name='logo',
        ),
        migrations.AddField(
            model_name='partner',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='partners'),
        ),
        migrations.AddField(
            model_name='partner',
            name='press_release',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='partners', to='core.pressrelease'),
        ),
    ]
