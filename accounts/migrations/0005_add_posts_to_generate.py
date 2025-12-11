# Generated migration for adding posts_to_generate field

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_logo_and_brand_analysis'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyprofile',
            name='posts_to_generate',
            field=models.IntegerField(
                default=10,
                help_text='Number of posts to generate at once (1-30)',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(30)
                ]
            ),
        ),
    ]



