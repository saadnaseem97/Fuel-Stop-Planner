import csv
from django.core.management.base import BaseCommand
from fuel_api.models import FuelStation

class Command(BaseCommand):
    help = 'Import fuel stations from CSV file'

    def handle(self, *args, **options):
        with open('fuel_prices.csv', 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                FuelStation.objects.create(
                    truckstop_id=row['OPIS Truckstop ID'],
                    truckstop_name=row['Truckstop Name'],
                    address=row['Address'],
                    city=row['City'],
                    state=row['State'],
                    rack_id=row['Rack ID'],
                    retail_price=row['Retail Price'],
                )
        self.stdout.write(self.style.SUCCESS('Successfully imported fuel stations'))