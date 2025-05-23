'''
SmartHealthPublisher.py is the base class based on MyMQTT class that puts the data into SenML fomat and publishes it.
'''

import pandas as pd
import time
import json
import os
from MyMQTT import MyMQTT

class Publisher:
    def __init__(self, client_id, broker, port):
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.client_mqtt = MyMQTT(client_id, broker, port)


    def start(self):
        self.client_mqtt.start()

    def publish_normal_data(self, topic, value, unit):
        message = {
            "bn": self.client_id,
            "e": [
                {
                    "n": topic.split('/')[-1],
                    "u": unit,
                    "t": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    "v": value
                }
            ]
        }
        self.client_mqtt.myPublish(topic, message)


    def stop(self):
        self.client_mqtt.stop()


