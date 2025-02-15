# Generated by Django 5.1.6 on 2025-02-08 02:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shieldmodel',
            name='max_ballistic_absorption',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='max_ballistic_resistance',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='max_distortion_absorption',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='max_distortion_resistance',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='max_energy_absorption',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='max_energy_resistance',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='max_power_slots',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='min_ballistic_absorption',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='min_ballistic_resistance',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='min_distortion_absorption',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='min_distortion_resistance',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='min_energy_absorption',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='min_energy_resistance',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='min_power_slots',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='name',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='size',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='shieldmodel',
            name='total_hp',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='ballistic_resistance',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='distortion_resistance',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='energy_resistance',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='max_weapon_power',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='name',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='pitch_rate',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='raw_data',
            field=models.JSONField(blank=True),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='shield_faces',
            field=models.IntegerField(blank=True, choices=[(0, 'None'), (1, 'Bubble'), (2, 'FrontBack'), (3, 'Quadrant')]),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='size',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='vital_hull_hp',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='shipmodel',
            name='vital_hull_name',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='accuracy',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='alpha_damage',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='ammo_count',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='burst_cooldown',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='burst_dps',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='burst_duration',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='damage_type',
            field=models.CharField(blank=True, choices=[(1, 'Physical'), (2, 'Energy'), (3, 'Distortion')], max_length=32),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='fire_rate',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='name',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='projectile_speed',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='raw_data',
            field=models.JSONField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='size',
            field=models.IntegerField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='sustained_dps',
            field=models.FloatField(blank=True),
        ),
        migrations.AlterField(
            model_name='weaponmodel',
            name='total_runtime',
            field=models.FloatField(blank=True),
        ),
    ]
