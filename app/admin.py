from django.contrib import admin 
from .models import ShipModel, LoadoutModel, WeaponModel, ShieldModel

# Register your models here.
admin.site.register(ShipModel)
admin.site.register(WeaponModel)
admin.site.register(LoadoutModel)
admin.site.register(ShieldModel)