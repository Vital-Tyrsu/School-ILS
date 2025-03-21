# Generated by Django 5.1.6 on 2025-03-11 12:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0002_book_publisher_alter_book_author_alter_book_genre_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='expiration_date',
            field=models.DateTimeField(db_index=True, help_text='e.g., 2025-03-13', verbose_name='Expiration Date'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='reservation_date',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Reservation Date'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('assigned', 'Assigned'), ('picked_up', 'Picked Up'), ('expired', 'Expired'), ('canceled', 'Canceled')], db_index=True, default='pending', max_length=10, verbose_name='Status'),
        ),
    ]
