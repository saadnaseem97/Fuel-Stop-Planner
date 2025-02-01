import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from django.shortcuts import render
from fuel_api.models import FuelStation
import numpy as np
from scipy.spatial import KDTree
import bisect

@csrf_exempt
def plan_route(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    data = json.loads(request.body)
    start_address = data.get('start')
    end_address = data.get('end')

    def geocode_address(addr):
        geolocator = Nominatim(user_agent="fuel_app")
        try:
            location = geolocator.geocode(f"{addr}, USA")
            return (location.latitude, location.longitude) if location else None
        except:
            return None

    start_coords = geocode_address(start_address)
    end_coords = geocode_address(end_address)

    if not start_coords or not end_coords:
        return JsonResponse({'error': 'Could not geocode addresses'}, status=400)

    route_url = f'http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=geojson'
    response = requests.get(route_url)
    if response.status_code != 200:
        return JsonResponse({'error': 'Routing failed'}, status=500)
    
    route_data = response.json()
    if route_data['code'] != 'Ok':
        return JsonResponse({'error': 'No route found'}, status=400)
    total_distance = route_data['routes'][0]['distance'] * 0.000621371
    route_geometry = route_data['routes'][0]['geometry']['coordinates']
    decoded_points = [(point[1], point[0]) for point in route_geometry]
    cumulative_distances = [0.0]
    for i in range(1, len(decoded_points)):
        prev = decoded_points[i-1]
        curr = decoded_points[i]
        cumulative_distances.append(cumulative_distances[-1] + geodesic(prev, curr).miles)
    
    # Optimized station filtering
    print("Starting station filtering")
    
    # Convert route points to numpy array
    route_points = np.array([(p[0], p[1]) for p in decoded_points])
    
    # Create KDTree for fast spatial queries
    route_tree = KDTree(route_points)
    
    # Get all stations with coordinates
    stations = FuelStation.objects.exclude(latitude__isnull=True, longitude__isnull=True).only(
        'latitude', 'longitude', 'truckstop_name', 'retail_price', 'address', 'city', 'state'
    )
    
    # Batch process stations using numpy
    station_coords = np.array([(s.latitude, s.longitude) for s in stations])
    
    # Find nearest route points for all stations at once
    distances, indices = route_tree.query(station_coords, k=1, distance_upper_bound=10/69)  # 10 miles in degrees approx
    
    # Filter and collect valid stations
    route_stations = []
    for i, station in enumerate(stations):
        if distances[i] <= 10/69:  # Approximately 10 miles
            station.distance_along_route = cumulative_distances[indices[i]]
            route_stations.append(station)
    
    print(f"Found {len(route_stations)} stations near route")
    route_stations.sort(key=lambda x: x.distance_along_route)

    station_distances = [s.distance_along_route for s in route_stations]
    current_position = 0.0
    total_cost = 0.0
    stops = []
    total_route_miles = cumulative_distances[-1]
    # Optimization: Find first station index after current position
    current_index = 0

    while current_position + 500 < total_route_miles:  # Need at least one stop
        # Find stations within 500 mile range using binary search
        max_range = current_position + 500
        start_idx = bisect.bisect_left(station_distances, current_position, current_index)
        end_idx = bisect.bisect_right(station_distances, max_range, start_idx)
        
        candidates = route_stations[start_idx:end_idx]
        current_index = start_idx  # Optimize next search
        
        if not candidates:
            return JsonResponse({'error': f'No stations between {current_position} and {max_range} miles'}, status=400)
        
        # Find the cheapest station in the furthest 100 miles (balance price vs distance)
        lookahead = max_range - 100  # Consider last 100 miles of range
        best_station = None
        best_price = float('inf')
        
        # Reverse search to find cheapest in the latter part of the range
        for station in reversed(candidates):
            if station.retail_price < best_price and station.distance_along_route >= lookahead:
                best_station = station
                best_price = station.retail_price
        
        # Fallback to global cheapest in range if no good lookahead
        if best_station is None:
            best_station = min(candidates, key=lambda x: x.retail_price)
        
        # Calculate fuel needed to reach this station
        distance_to_station = best_station.distance_along_route - current_position
        fuel_needed = distance_to_station / 10
        
        # Update state
        total_cost += fuel_needed * best_station.retail_price
        current_position = best_station.distance_along_route
        
        stops.append({
            'name': best_station.truckstop_name,
            'address': f"{best_station.address}, {best_station.city}, {best_station.state}",
            'latitude': best_station.latitude,
            'longitude': best_station.longitude,
            'cost': round(fuel_needed * best_station.retail_price, 2),
            'retail_price': best_station.retail_price,
            'distance_from_start': round(current_position, 2),
        })

    # Add final stretch if needed
    if current_position < total_route_miles:
        final_distance = total_route_miles - current_position
        if final_distance > 500:
            return JsonResponse({'error': 'Cannot reach destination from last station'}, status=400)
        fuel_needed = final_distance / 10
        # Add cost of fuel already in tank for final stretch
        total_cost += fuel_needed * stops[-1]['retail_price'] if stops else 0

    return JsonResponse({
        'route': {
            'geometry': route_geometry,
            'total_distance_miles': round(total_route_miles, 2),
        },
        'fuel_stops': stops,
        'total_cost': round(total_cost, 2),
    })

def map_view(request):
    return render(request, 'fuel_map.html')