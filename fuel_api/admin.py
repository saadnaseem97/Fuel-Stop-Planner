from django.contrib import admin
from .models import FuelStation

@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    list_display = ('truckstop_name', 'city', 'state', 'retail_price', 
                    'latitude', 'longitude', 'geocode_success')
    search_fields = ('truckstop_name', 'city', 'state')
    list_filter = ('state', 'geocode_success')