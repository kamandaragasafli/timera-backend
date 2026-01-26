# Generated manually for gradient settings

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_companyprofile_slogan_position_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyprofile',
            name='gradient_enabled',
            field=models.BooleanField(default=True, help_text='Apply gradient overlay behind logo/slogan'),
        ),
        migrations.AddField(
            model_name='companyprofile',
            name='gradient_color',
            field=models.CharField(default='#3B82F6', help_text='Gradient color (hex code)', max_length=7),
        ),
        migrations.AddField(
            model_name='companyprofile',
            name='gradient_height_percent',
            field=models.IntegerField(default=25, help_text='Gradient height as percentage of image height (10-50%)', validators=[django.core.validators.MinValueValidator(10), django.core.validators.MaxValueValidator(50)]),
        ),
        migrations.AddField(
            model_name='companyprofile',
            name='gradient_position',
            field=models.CharField(choices=[('top', 'Top'), ('bottom', 'Bottom'), ('both', 'Both')], default='both', help_text='Where to apply gradient', max_length=10),
        ),
        migrations.AlterField(
            model_name='companyprofile',
            name='logo_position',
            field=models.CharField(choices=[('top-center', 'Top Center'), ('bottom-center', 'Bottom Center')], default='top-center', help_text='Logo position on images', max_length=20),
        ),
    ]

