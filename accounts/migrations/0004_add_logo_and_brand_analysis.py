# Generated migration for adding logo and brand_analysis fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_canva_integration'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyprofile',
            name='logo',
            field=models.ImageField(blank=True, help_text='Company logo', null=True, upload_to='company_logos/'),
        ),
        migrations.AddField(
            model_name='companyprofile',
            name='brand_analysis',
            field=models.JSONField(blank=True, default=dict, help_text='AI-analyzed brand information from logo'),
        ),
    ]



