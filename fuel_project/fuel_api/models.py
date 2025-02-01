from django.db import models

class FuelStation(models.Model):
    truckstop_id = models.IntegerField()
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    retail_price = models.FloatField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    geocode_attempted_at = models.DateTimeField(null=True, blank=True)
    geocode_success = models.BooleanField(default=False)

    def __str__(self):
        return self.truckstop_name