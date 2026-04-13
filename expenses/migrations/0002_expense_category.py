from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='category',
            field=models.CharField(
                choices=[
                    ('Food', 'Food'),
                    ('Transport', 'Transport'),
                    ('Books', 'Books'),
                    ('Health', 'Health'),
                    ('Entertainment', 'Entertainment'),
                    ('Other', 'Other'),
                ],
                default='Other',
                max_length=50,
            ),
        ),
    ]
