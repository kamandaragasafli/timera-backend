# Manual migration for branding positions and slogan size

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_add_gradient_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyprofile',
            name='slogan_size_percent',
            field=models.IntegerField(
                default=4,
                help_text='Slogan font size as percentage of image height (2-8%)',
                validators=[
                    django.core.validators.MinValueValidator(2),
                    django.core.validators.MaxValueValidator(8)
                ]
            ),
        ),
        migrations.AlterField(
            model_name='companyprofile',
            name='logo_position',
            field=models.CharField(
                choices=[
                    ('top-center', 'Top Center'),
                    ('top-left', 'Top Left'),
                    ('top-right', 'Top Right'),
                    ('bottom-center', 'Bottom Center'),
                    ('bottom-left', 'Bottom Left'),
                    ('bottom-right', 'Bottom Right'),
                ],
                default='top-center',
                help_text='Logo position on images',
                max_length=20
            ),
        ),
    ]

