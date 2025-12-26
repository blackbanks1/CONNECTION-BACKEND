"""
Route calculation service for distance and ETA
"""

import requests
import math
from datetime import datetime, timedelta
from config import RWANDA_BOUNDS
class RouteService:
    """Service for calculating routes, distances, and ETAs"""
    
    # Rwanda bounding box coordinates (approximate)
    RWANDA_BOUNDS = {
        'min_lat': -2.84,
        'max_lat': -1.05,
        'min_lon': 28.86,
        'max_lon': 30.90
    }
    
    @staticmethod
    def validate_coordinates(lat, lon):
        """Validate if coordinates are within Rwanda"""
        return (RWANDA_BOUNDS['min_lat'] <= lat <= RWANDA_BOUNDS['max_lat'] and
                RWANDA_BOUNDS['min_lon'] <= lon <= RWANDA_BOUNDS['max_lon'])
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth's radius in kilometers
        return round(c * r, 2)
    
    @staticmethod
    def calculate_eta(distance_km, traffic_factor=1.0, vehicle_type='motorcycle'):
        """
        Calculate Estimated Time of Arrival
        
        Args:
            distance_km: Distance in kilometers
            traffic_factor: 1.0 = normal, 1.5 = heavy traffic, 2.0 = very heavy
            vehicle_type: 'motorcycle', 'car', 'truck'
        
        Returns:
            Tuple: (eta_minutes, arrival_time_iso)
        """
        # Average speeds in km/h for Kigali/Rwanda
        speeds = {
            'motorcycle': 40,
            'car': 30,
            'truck': 20
        }
        
        base_speed = speeds.get(vehicle_type, 30)
        effective_speed = base_speed / traffic_factor
        
        # Calculate time in hours, then convert to minutes
        time_hours = distance_km / effective_speed
        eta_minutes = round(time_hours * 60)
        
        # Add buffer for traffic lights, stops, etc.
        eta_minutes = int(eta_minutes * 1.2)  # 20% buffer
        
        # Calculate arrival time
        arrival_time = datetime.utcnow() + timedelta(minutes=eta_minutes)
        
        return eta_minutes, arrival_time.isoformat()
    
    @staticmethod
    def get_route_polyline(origin_lat, origin_lon, dest_lat, dest_lon):
        """
        Get route polyline from OSRM (Open Source Routing Machine)
        
        Note: For production, you might want to use a commercial service
        like Mapbox, Google Maps, or set up your own OSRM server
        """
        try:
            # Using public OSRM demo server (replace with your own in production)
            base_url = "https://router.project-osrm.org/route/v1/driving/"
            coordinates = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
            url = f"{base_url}{coordinates}?overview=full&geometries=geojson"
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 'Ok' and data.get('routes'):
                    route = data['routes'][0]
                    geometry = route['geometry']
                    distance_meters = route['distance']
                    duration_seconds = route['duration']
                    
                    return {
                        'polyline': geometry,
                        'distance_km': round(distance_meters / 1000, 2),
                        'duration_minutes': round(duration_seconds / 60),
                        'success': True
                    }
            
            # Fallback to straight-line distance if routing fails
            distance_km = RouteService.calculate_distance(
                origin_lat, origin_lon, dest_lat, dest_lon
            )
            eta_minutes, arrival_time = RouteService.calculate_eta(distance_km)
            
            return {
                'polyline': None,
                'distance_km': distance_km,
                'duration_minutes': eta_minutes,
                'success': False,
                'message': 'Using straight-line distance'
            }
            
        except Exception as e:
            print(f"Route service error: {str(e)}")
            # Fallback calculation
            distance_km = RouteService.calculate_distance(
                origin_lat, origin_lon, dest_lat, dest_lon
            )
            eta_minutes, arrival_time = RouteService.calculate_eta(distance_km)
            
            return {
                'polyline': None,
                'distance_km': distance_km,
                'duration_minutes': eta_minutes,
                'success': False,
                'message': str(e)
            }

# Singleton instance
route_service = RouteService()