'''
SmartHealthTelegram.py is a service to integrate the proposed infrastructure into Telegram platform, 
which is cloud-based instant messaging infrastructure. It also allows users on sending request commands to IoT devices. 
It is Consumer of Catalogue to read configuration exploiting REST. 
Telegram bot is a MQTT subscriber to GPS Tracking based on ("SmartHealth/{user_id}/danger/gps")  when the user is 
out of the safe area it sends alert message and html file and also, the caregiver can request data from wearable device 
to get real-time heart rate value and blood oxygen value and it is consumer of cataloge for authorizing user name and 
password of users.
'''

import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton
import json
from threading import Thread
from WearableDevice import WearableDevice
from MyMQTT import MyMQTT
from GPS_Tracker import GPSTracker
import logging

class Bot:
    def __init__(self, token, mqtt_broker, mqtt_port):
        self.bot = telepot.Bot(token)
        self.users = self.load_users_from_json("catalog.json")
        self.mqtt_client = MyMQTT("clientID", mqtt_broker, mqtt_port, self.on_mqtt_message)
        self.mqtt_client.start()
        self.chat_contexts = {}  # To store chat specific data and contexts
        self.subscriptions = {}  # To track subscriptions
        self.last_message_time = {}
        self.latest_values = {}
        self.wearable_device = WearableDevice()  # Initialize the wearable device
        self.home_lat = self.wearable_device.home_lat
        self.home_lon = self.wearable_device.home_lon
        self.gps_tracker = GPSTracker()

        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def load_users_from_json(self, filename):
        with open(filename, "r") as file:
            data = json.load(file)
            users = {}
            for user in data["users"]:
                users[user["username"]] = {"password": user["password"], "userID": user["userID"], "chat_id": None, "stage": None}
            return users

    def subscribe_all(self, user_id):
        all_topics = [f"SmartHealth/{user_id}/danger/heart_rate",
                      f"SmartHealth/{user_id}/danger/blood_oxygen",
                      f"SmartHealth/{user_id}/danger/gps",
                      f"SmartHealth/{user_id}/heart_rate",
                      f"SmartHealth/{user_id}/blood_oxygen"]
        for topic in all_topics:
            self.mqtt_client.mySubscribe(topic)
            self.track_subscription(user_id, topic)

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type != 'text':
            return  # ignore non-text messages
        text = msg['text']
        if text == "/start":
            self.bot.sendMessage(chat_id, "Please enter your username:", reply_markup=self.make_start_keyboard())
            self.chat_contexts[chat_id] = {"stage": "username"}
        elif text == "/stop":
            self.stop_updates(chat_id)
        else:
            user_data = self.chat_contexts.get(chat_id, {})
            if user_data.get("stage") == "username":
                if text in self.users:
                    self.chat_contexts[chat_id] = {"username": text, "stage": "password"}
                    self.bot.sendMessage(chat_id, "Please enter your password:")
                else:
                    self.bot.sendMessage(chat_id, "Invalid username. Please try again or use /start to begin.")
            elif user_data.get("stage") == "password":
                username = user_data.get("username")
                if text == self.users[username]["password"]:
                    self.bot.sendMessage(chat_id, "Login successful! If your blood oxygen or heart rate goes into a dangerous range, we will notify you.")
                    self.bot.sendMessage(chat_id, "Select an option:", reply_markup=self.make_main_keyboard())
                    self.chat_contexts[chat_id]["stage"] = "logged_in"
                    self.chat_contexts[chat_id]["userID"] = self.users[username]["userID"]
                    self.users[username]["chat_id"] = chat_id  # Save chat_id for notifications
                    self.subscribe_all(self.users[username]['userID'])
                    Thread(target=self.wearable_device.process_user_file, args=(username,)).start()
                else:
                    self.bot.sendMessage(chat_id, "Incorrect password. Please try again.")
                    self.bot.sendMessage(chat_id, "Please enter your password:")
            elif user_data.get("stage") == "logged_in":
                if text == "Get Heart Rate":
                    self.send_latest_value(chat_id, user_data["userID"], 'heart_rate')
                elif text == "Get Blood Oxygen":
                    self.send_latest_value(chat_id, user_data["userID"], 'blood_oxygen')
                elif text == "Stop Updates":
                    self.stop_updates(chat_id)
                elif text == "Update":
                    self.bot.sendMessage(chat_id, "Restarting with new user ID...")
                    self.start_new_login(chat_id)
                elif text == "Continue":
                    self.bot.sendMessage(chat_id, "Continuing with the current subscriptions...")
                    self.bot.sendMessage(chat_id, "Select an option:", reply_markup=self.make_main_keyboard())
                elif text == "Finish":
                    self.finish_subscriptions(chat_id)

    def stop_updates(self, chat_id):
        if chat_id in self.chat_contexts:
            keyboard = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="Update")],
                [KeyboardButton(text="Continue")],
                [KeyboardButton(text="Finish")]
            ], one_time_keyboard=True)
            self.bot.sendMessage(chat_id, "What would you like to do?", reply_markup=keyboard)

    def make_start_keyboard(self):
        keyboard = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="/start")]
        ], one_time_keyboard=True)
        return keyboard

    def make_main_keyboard(self):
        keyboard = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="Get Heart Rate")],
            [KeyboardButton(text="Get Blood Oxygen")],
            [KeyboardButton(text="Stop Updates")]
        ], one_time_keyboard=True)
        return keyboard

    def on_callback_msg(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        chat_context = self.chat_contexts.get(from_id, {})
        userID = chat_context.get("userID")
        if query_data == 'get_heart_rate':
            self.send_latest_value(from_id, userID, 'heart_rate')
        elif query_data == 'get_blood_oxygen':
            self.send_latest_value(from_id, userID, 'blood_oxygen')
        elif query_data == 'stop_updates':
            self.stop_updates(from_id)
        elif query_data == 'update':
            self.bot.sendMessage(from_id, "Restarting with new user ID...")
            self.start_new_login(from_id)
        elif query_data == 'continue':
            self.bot.sendMessage(from_id, "Continuing with the current subscriptions...")
            self.bot.sendMessage(from_id, "Select an option:", reply_markup=self.make_main_keyboard())
        elif query_data == 'finish':
            self.finish_subscriptions(from_id)
        self.bot.answerCallbackQuery(query_id, text=f"{query_data.title()} option selected.")

    def send_latest_value(self, from_id, user_id, data_type):
        message_key = f"{user_id}_{data_type}"
        if message_key in self.latest_values:
            value, unit, timestamp = self.latest_values[message_key]
            user_name = next((u for u in self.users if self.users[u]["userID"] == int(user_id)), "User")
            friendly_message = f"The latest {data_type.replace('_', ' ').title()} for {user_name} is {value} {unit} at {timestamp}."
            self.bot.sendMessage(from_id, friendly_message)
        else:
            self.bot.sendMessage(from_id, "No data available yet.")

    def finish_subscriptions(self, chat_id):
        if chat_id in self.chat_contexts:
            userID = self.chat_contexts[chat_id].get("userID")
            if userID:
                if userID in self.subscriptions:
                    for topic in self.subscriptions[userID]:
                        self.mqtt_client.unsubscribe(topic)
                    del self.subscriptions[userID]
            del self.chat_contexts[chat_id]
            self.bot.sendMessage(chat_id, "You have been unsubscribed from updates.")

    def start_new_login(self, chat_id):
        # Clear any existing context and start fresh
        self.chat_contexts[chat_id] = {"stage": "username"}
        self.bot.sendMessage(chat_id, "Please enter your username:")

    def track_subscription(self, userID, topic):
        if userID not in self.subscriptions:
            self.subscriptions[userID] = []
        if topic not in self.subscriptions[userID]:
            self.subscriptions[userID].append(topic)

    def on_mqtt_message(self, topic, payload):
        topic_parts = topic.split('/')
        user_id = topic_parts[1]
        data_type = topic_parts[3] if 'danger' in topic_parts else topic_parts[2]
        payload = json.loads(payload)
        value = payload['e'][0]['v']
        timestamp = payload['e'][0]['t']
        unit = payload['e'][0]['u']
        message_key = f"{user_id}_{data_type}"
        current_time = time.time()
        debounce_period = 1  # seconds
        self.latest_values[message_key] = (value, unit, timestamp)
        # Check if the message should be processed now
        if message_key not in self.last_message_time or (
                current_time - self.last_message_time[message_key] > debounce_period):
            self.last_message_time[message_key] = current_time
            user_name = next((u for u in self.users if self.users[u]["userID"] == int(user_id)), "User")
            for chat_id, context in self.chat_contexts.items():
                if context.get("userID") == int(user_id):
                    if 'danger' in topic_parts:
                        self.handle_danger_message(topic_parts, user_name, chat_id, value, unit, user_id, data_type)

    def handle_danger_message(self, topic_parts, user_name, chat_id, value, unit, user_id, data_type):
        if 'gps' in topic_parts:
            html_file_path = self.gps_tracker.create_html_map(value.split(",")[0], value.split(",")[1], user_id)
            with open(html_file_path, 'rb') as f:
                self.bot.sendDocument(chat_id, f, "Warning! Your patient is out of zone! Here is the current location of your patient.")
        elif 'heart_rate' in topic_parts or 'blood_oxygen' in topic_parts:
            friendly_message = f"Warning! {user_name}'s {data_type.replace('_', ' ').title()} is at a dangerous level: {value}{unit}."
            self.bot.sendMessage(chat_id, friendly_message)

    def handle_regular_message(self, user_name, data_type, value, unit, timestamp, chat_id):
        friendly_message = f"The latest {data_type.replace('_', ' ').title()} for {user_name} is {value} {unit} at {timestamp}."
        self.bot.sendMessage(chat_id, friendly_message)

    def run(self):
        MessageLoop(self.bot, {'chat': self.on_chat_message, 'callback_query': self.on_callback_msg}).run_as_thread()
        print('Bot is listening ...')

        while 1:
            time.sleep(1)

if __name__ == "__main__":
    token = "7148598555:AAH1ZwQWtdQ2g--nOimGMz_Ufy5x0UxUnbI"  # Replace with your actual token
    mqtt_broker = 'mqtt.eclipseprojects.io'
    mqtt_port = 1883
    bot = Bot(token, mqtt_broker, mqtt_port)
    bot.run()
