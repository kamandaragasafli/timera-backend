# Generated migration for Canva integration fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_companyprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='canva_access_token',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='canva_refresh_token',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='canva_token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]





