# Generated by Django 5.1.1 on 2025-01-27 07:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="client",
            name="website",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="journalist",
            name="title",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]
