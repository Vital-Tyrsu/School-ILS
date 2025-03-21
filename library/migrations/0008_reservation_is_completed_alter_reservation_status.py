# Generated by Django 5.1.6 on 2025-03-17 16:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0007_alter_reservation_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='is_completed',
            field=models.BooleanField(default=False, verbose_name='Completed'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('assigned', 'Assigned'), ('picked_up', 'Picked Up'), ('expired', 'Expired'), ('canceled', 'Canceled')], default='pending', max_length=10, verbose_name='Status'),
        ),
    ]
