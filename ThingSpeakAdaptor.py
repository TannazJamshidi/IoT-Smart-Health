'''
ThingSpeakAdaptor.py is an MQTT subscriber that receives measurements on heart rate and blood oxygen and upload them 
on Thinkspeak through REST Web Services. Thingspeak Adaptor is a REST consumer of catalog for reading configuration. 
It also has a MQTT commiunication and subscriber of ("SmartHealth/{user_id}/heart_rate"), 
("SmartHealth/{user_id}/blood_oxygen") to get processed data of heart rate and blood oxygen through message broker.
'''

import json
import requests
import time
import logging
from MyMQTT import MyMQTT

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ThingSpeakSubscriber:
    """Class to handle subscription and posting data to ThingSpeak."""
    def __init__(self):
        self.load_catalog()
        self.broker = 'mqtt.eclipseprojects.io'
        self.port = 1883
        self.client_id = 'ThingSpeakAdaptor'
        self.client_mqtt = MyMQTT(self.client_id, self.broker, self.port, self.on_message)
        self.user_field_maps = self.define_field_mappings()

    def start(self):
        self.client_mqtt.start()
        self.subscribe_to_topics()

    def subscribe_to_topics(self):
        for topic in self.topics:
            self.client_mqtt.mySubscribe(topic)

    def load_catalog(self):
        # Load catalog data to determine which topics to subscribe to and map user-specific API keys
        try:
            with open('Catalog.json', 'r') as f:
                catalog = json.load(f)
                self.topics = []
                self.user_api_keys = {}
                for user in catalog['users']:
                    user_id = user['userID']
                    #api_key = user['thingSpeakWriteAPIKey']
                    #self.user_api_keys[user_id] = api_key
                    self.topics.append(f"SmartHealth/{user_id}/heart_rate")
                    self.topics.append(f"SmartHealth/{user_id}/blood_oxygen")
        except Exception as e:
            logging.error(f"Error loading catalog: {e}")

    def define_field_mappings(self):
        # Define field mappings based on user ID
        return {
            1: {'heart_rate': 'field1', 'blood_oxygen': 'field2'},
            2: {'heart_rate': 'field3', 'blood_oxygen': 'field4'},
            3: {'heart_rate': 'field5', 'blood_oxygen': 'field6'},
            4: {'heart_rate': 'field7', 'blood_oxygen': 'field8'}
        }

    def on_message(self, topic, payload):
        try:
            msg = json.loads(payload)
            user_id = int(topic.split('/')[1])
            data_type = topic.split('/')[-1]
            value = msg['e'][0]['v']
            self.post_to_thingspeak(user_id, data_type, value)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON payload from topic {topic}")
        except Exception as e:
            logging.error(f"Failed to process message from topic {topic}: {e}")

    def post_to_thingspeak(self, user_id, data_type, value):
        try:
            #api_key = self.user_api_keys.get(user_id)
            api_key = "L2ENIY2E42E4AT5J"
            if not api_key:
                logging.error(f"API key for user {user_id} not found.")
                return

            field = self.user_field_maps[user_id].get(data_type)
            if not field:
                logging.error(f"Invalid data type {data_type} for user {user_id}")
                return

            url = f"https://api.thingspeak.com/update"
            payload = {
                'api_key': api_key,
                field: value
            }
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                logging.info(f"Successfully posted {data_type} data to ThingSpeak for user {user_id}")
            else:
                logging.error(f"Failed to post data to ThingSpeak: {response.status_code}, {response.text}")
        except Exception as e:
            logging.error(f"Exception while posting to ThingSpeak: {e}")

    def stop(self):
        self.client_mqtt.stop()

if __name__ == "__main__":
    subscriber = ThingSpeakSubscriber()
    subscriber.start()
    try:
        while True:
            time.sleep(1)  # Keep the subscriber running
    except KeyboardInterrupt:
        subscriber.stop()
