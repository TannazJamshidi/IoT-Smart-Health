'''
WearableDevice.py is a digital bracelet which is directly connected to the internet, it has a narrow space to 
put an eSIM inside it in order to connect the device to internet connection. It is a REST consumer of Catalogue to 
read the configuration of sensors. It compares the values of each sensor if they are out of range caregiver get an 
alert message through Telegram bot so Wearable device is a publisher and publishes the sensed data of heart rate 
through ("SmartHealth/{user_id}/heart_rate") and blood oxygen based on ("SmartHealth/{user_id}/blood_oxygen") 
to ThingSpeak Adaptor and publishes data based on ("SmartHealth/{user_id}/danger/{data_type}") to 
Telegram bot for alerts in case patient gets out of zone or their heart rate or blood oxygen is out of standard range. 
The caregiver can get request for real-time values of heart rate and blood oxygen for the latest value. 
Also, it consists of three sensors:
1.	Heart Rate Sensor:
Unit of Measurement: Beats per Minute (BPM)
Normal Range for Elderly Individuals (Restin):
Resting heart rate can vary, but a typical range for elderly individuals at rest might be between 60 to 100 BPM. 
2.	GPS Sensor:
Unit of Measurement: Latitude and Longitude coordinates.
Normal range is the 500 meters from the patient’s house.
3.	Blood Oxygen Sensor (Pulse Oximeter):
Unit of Measurement: Percentage of Oxygen Saturation in Hemoglobin (% SpO2)
Normal Range for Elderly Individuals: A normal range for blood oxygen saturation is typically considered to be 
between 90% and 100%.

'''

import os
import json
import pandas as pd
import time
import logging
from SmartHealthPublisher import Publisher
from GPS_Tracker import GPSTracker

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WearableDevice:
    """Class to handle wearable device data publishing."""
    def __init__(self):
        self.broker = 'mqtt.eclipseprojects.io'
        self.port = 1883
        self.publisher = self.initialize_publisher()
        self.gps_tracker = GPSTracker()
        # Load user catalog
        try:
            with open('Catalog.json', 'r') as f:
                self.catalog = json.load(f)
                self.users = {user['username']: user for user in self.catalog['users']}
                self.home_lat = None
                self.home_lon = None
        except Exception as e:
            logging.error(f"Error loading catalog: {e}")

    def initialize_publisher(self):
        client_id = "wearable_device_publisher"
        publisher = Publisher(client_id, self.broker, self.port)
        publisher.start()
        return publisher

    def start(self):
        """Start the publishing process for all users in the catalog."""
        try:
            for username in self.users:
                self.process_user_file(username)
        except Exception as e:
            logging.error(f"Error starting the publishing process: {e}")

    def process_user_file(self, username):
        try:
            user = self.users.get(username)
            self.home_lat = user['latitude']
            self.home_lon = user['longitude']
            filename = f"{username}.csv"
            if not os.path.exists(filename):
                logging.warning(f"File {filename} does not exist for user {username}.")
                return
            df = pd.read_csv(filename)
            user_id = user['userID']
            for index, row in df.iterrows():
                self.publish_sensor_data(user_id, row, username)
                time.sleep(1)  # Simulate real-time data publishing
            logging.info(f"Successfully processed and published data from {filename}")
        except Exception as e:
            logging.error(f"Failed to process file for user {username}: {e}")

    def publish_sensor_data(self, user_id, row, username):
        required_keys = ['Heart Rate', 'Blood Oxygen', 'Latitude', 'Longitude', 'Time']
        if not all(key in row for key in required_keys):
            logging.warning("Missing data in input.")
            return

        self.publish_heart_rate(user_id, row["Heart Rate"], username)
        self.publish_blood_oxygen(user_id, row["Blood Oxygen"], username)

        if not pd.isna(row["Latitude"]) and not pd.isna(row["Longitude"]):
            self.publish_gps(user_id, row["Latitude"], row["Longitude"], username)

    def publish_heart_rate(self, user_id, heart_rate, username):
        topic = f"SmartHealth/{user_id}/heart_rate"
        if 60 < heart_rate < 100:
            self.publish_data(topic, heart_rate, unit='bpm')
        else:
            self.publish_danger_data(user_id, "heart_rate", heart_rate, username)

    def publish_blood_oxygen(self, user_id, blood_oxygen, username):
        topic = f"SmartHealth/{user_id}/blood_oxygen"
        blood_oxygen *= 100  # Convert blood oxygen to percentage if it is in decimal form
        if blood_oxygen < 90:
            self.publish_danger_data(user_id, "blood_oxygen", blood_oxygen, username)
        else:
            self.publish_data(topic, blood_oxygen, '%SpO2')

    def publish_gps(self, user_id, lat, lon, username):
        topic = f"SmartHealth/{user_id}/gps"
        distance = self.gps_tracker.distance(self.home_lat, self.home_lon, lat, lon)
        if distance > 500:
            self.publish_danger_data(user_id, "gps", f"{lat},{lon}", username)
        else:
            self.publish_data(topic, f"{lat},{lon}", 'coords')

    def publish_data(self, topic, value, unit):
        try:
            self.publisher.publish_normal_data(topic, value, unit)
            logging.info(f"Published data to {topic} successfully")
        except Exception as e:
            logging.error(f"Failed to publish data to {topic}: {e}")

    def publish_danger_data(self, user_id, data_type, value, username):
        unit_mapping = {
            "blood_oxygen": "%",
            "heart_rate": "bpm",
            "gps": "coords"
        }
        unit = unit_mapping.get(data_type, "")
        topic = f"SmartHealth/{user_id}/danger/{data_type}"
        self.publisher.publish_normal_data(topic, value, unit)
        logging.info(f"Published danger data to {topic} successfully")

    def stop_publisher(self):
        if self.publisher:
            self.publisher.stop()

    def __del__(self):
        self.stop_publisher()  # Ensure the publisher is stopped properly


