# fuel_api/management/commands/geocode_stations.py

import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q
from fuel_api.models import FuelStation
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Geocode stations using LocationIQ with daily request limits'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geocoded_count = 0
        self.max_daily_requests = 4800  # Stay under 5000 daily limit
        self.request_delay = 0.5  # 2 requests/second (LocationIQ limit)
        self.retry_delay = 60  # 1 minute for rate limit errors

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force processing even if daily limit might be exceeded'
        )

    def geocode_address(self, address):
        """Geocode an address using LocationIQ API"""
        try:
            response = requests.get(
                'https://us1.locationiq.com/v1/search',
                params={
                    'key': settings.LOCATIONIQ_KEY,
                    'q': address,
                    'format': 'json',
                    'countrycodes': 'us',
                    'limit': 1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return (float(data[0]['lat']), float(data[0]['lon']))
            elif response.status_code == 429:
                self.stdout.write(self.style.ERROR('Rate limit exceeded - waiting 1 minute'))
                time.sleep(self.retry_delay)
                return self.geocode_address(address)  # Retry once
                
            return None
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Geocoding error: {str(e)}'))
            return None

    def handle(self, *args, **options):
        # Get stations that need geocoding (prioritize never attempted)
        stations = FuelStation.objects.filter(
            Q(latitude__isnull=True) | 
            Q(longitude__isnull=True)
        ).order_by('geocode_attempted_at', 'id')[:self.max_daily_requests]

        total = stations.count()
        self.stdout.write(f'Processing {total} stations')

        for idx, station in enumerate(stations, 1):
            if self.geocoded_count >= self.max_daily_requests and not options['force']:
                self.stdout.write(self.style.WARNING('Daily request limit reached'))
                break

            # Build address string
            address = f"{station.address}, {station.city}, {station.state}, USA"
            
            self.stdout.write(f"\nProcessing {idx}/{total}: {station.truckstop_name}")
            self.stdout.write(f"Address: {address}")

            # Attempt geocoding
            coords = self.geocode_address(address)
            
            if coords:
                station.latitude, station.longitude = coords
                station.geocode_attempted_at = timezone.now()
                station.geocode_success = True
                station.save()
                self.geocoded_count += 1
                self.stdout.write(self.style.SUCCESS(f"Geocoded → {coords}"))
            else:
                station.geocode_attempted_at = timezone.now()
                station.save()
                self.stdout.write(self.style.WARNING("Geocoding failed"))

            # Maintain rate limit
            time.sleep(self.request_delay)

        self.stdout.write(self.style.SUCCESS(
            f"Finished processing {self.geocoded_count} stations. "
            f"Remaining daily capacity: {4500 - self.geocoded_count}"
        ))