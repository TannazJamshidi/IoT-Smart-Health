'''
GPS_Tracker.py is used to monitor patients’ location and check if they are getting far from their homes. 
In this IoT platform we are using ”folium” library of Python to demonstrate the location of users on the map. 
It consists of functions for calculating distance and creating html file and it is used in Telegram bot 
through Object-Oriented Programming (OOP). 
'''

import folium
import pandas as pd
import math

class GPSTracker:

    def create_html_map(self, latitude, longitude, user_id):
        # Create a map centered around the given latitude and longitude
        map_object = folium.Map(location=[latitude, longitude], zoom_start=10)

        # Add a marker for the user's location
        folium.Marker(location=[latitude, longitude], popup=f"User {user_id} Location").add_to(map_object)

        # Save the map as an HTML file
        html_file_path = f"map_{user_id}.html"
        map_object.save(html_file_path)

        return html_file_path

    def distance(self, lat1, lon1, lat2, lon2):
        # Haversine formula
        R = 6371e3  # Radius of Earth in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
