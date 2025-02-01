# Fuel Stop Planner - Optimal Route and Fuel Cost Calculator

A Django-based application that calculates optimal fuel stops along a route in the USA, considering fuel prices and vehicle range.

## Features

- 🗺️ Route planning using OSRM's routing engine
- ⛽ Fuel station database with real-time geocoding
- 💰 Optimal fuel stop selection based on price and range
- 📊 Cost calculation (10 MPG assumption)
- 🗺️ Interactive Leaflet.js map visualization
- 🚀 Bulk geocoding with LocationIQ integration
- 📈 Spatial optimization using SciPy's KDTree

## Installation

### Prerequisites
- Python 3.8+
- Django 3.2.23
- LocationIQ API key (free tier)

```bash
# Clone repository
git clone https://github.com/yourusername/fuel-planner.git
cd fuel-planner

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac)
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
echo "LOCATIONIQ_KEY=your_api_key_here" > .env

# Database setup
python manage.py migrate
python manage.py import_fuel_stations
python manage.py geocode_stations

```

## Usage

```bash
# Start development server
python manage.py runserver
```
Access the web interface at http://localhost:8000

### Example Input:
Start: "New York, NY"

End: "Los Angeles, CA"

## API Documentation

Endpoint: POST /api/plan_route/


### Request Body:

```json
{
    "start": "Chicago, IL",
    "end": "Miami, FL"
}
```

### Successful Response:

```json
{
    "route": {
        "geometry": [[-87.6298,41.8781], ...],
        "total_distance_miles": 1503.2
    },
    "fuel_stops": [
        {
            "name": "PILOT #1243",
            "address": "I-8, Exit 119, Gila Bend, AZ",
            "cost": 45.50,
            "distance_from_start": 423.1
        }
    ],
    "total_cost": 245.75
}
```

## Database Schema
### FuelStation Model

```python
class FuelStation(models.Model):
    truckstop_id = models.IntegerField()
    truckstop_name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    retail_price = models.FloatField()
    geocode_attempted_at = models.DateTimeField(null=True)
    geocode_success = models.BooleanField(default=False)
```

## Optimization Techniques
1. Spatial Indexing
- Uses SciPy's KDTree for O(log n) nearest-neighbor searches
- Batch processes stations using NumPy arrays

2. Route Optimization

- Lookahead algorithm balances price vs distance
- Binary search for efficient candidate selection

3. Geocoding
- Daily request limit handling
- Automatic retry on API errors

## Troubleshooting
### Common Issues:

1. Geocoding Failures:

```bash
# Check failed geocodes
python manage.py shell
>>> from fuel_api.models import FuelStation
>>> FuelStation.objects.filter(geocode_success=False).count()
```
2. Routing Errors:

```bash
# Test OSRM directly
curl "http://router.project-osrm.org/route/v1/driving/-87.6298,41.8781;-80.1918,25.7617"
```

## Acknowledgments
- Route data from OSRM
- Geocoding by LocationIQ
- Fuel price data from OPIS
- Map visualization with Leaflet
