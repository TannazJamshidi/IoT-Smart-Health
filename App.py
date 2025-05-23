'''
App.py provides a RESTful web service for managing users and devices in an IoT platform by performing basic 
CRUD (Create, Read, Update, Delete) operations on a catalog file (Catalog.json).
'''

import cherrypy
import json
import os
from datetime import datetime

catalog_file = 'Catalog.json'


def load_catalog():
    with open(catalog_file, 'r') as f:
        return json.load(f)


def save_catalog(catalog):
    with open(catalog_file, 'w') as f:
        json.dump(catalog, f, indent=4)


class UserService(object):
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def add_user(self):
        data = cherrypy.request.json
        try:
            catalog = load_catalog()
            users = catalog['users']
            new_user_id = max(user['userID'] for user in users) + 1
            new_user = {
                "userID": new_user_id,
                "name": data['name'],
                "surname": data['surname'],
                "username": data['username'],
                "password": data['password'],
                "latitude": data['latitude'],
                "longitude": data['longitude'],
                "csvFile": f"{data['username']}.csv",
                "thingSpeakChannelID": data['thingSpeakChannelID'],
                "thingSpeakWriteAPIKey": data['thingSpeakWriteAPIKey']
            }
            users.append(new_user)
            catalog['lastUpdate'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_catalog(catalog)
            return {"message": "User added successfully"}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def update_user(self):
        data = cherrypy.request.json
        try:
            catalog = load_catalog()
            users = catalog['users']
            user = next((user for user in users if user['username'] == data['username'] and user['password'] == data['password']), None)

            if not user:
                return {"error": "Invalid username or password"}

            # Update fields if provided
            for key in ['name', 'surname', 'new_username', 'new_password', 'latitude', 'longitude', 'thingSpeakChannelID', 'thingSpeakWriteAPIKey']:
                if key in data and data[key]:
                    user[key.split("new_")[-1]] = data[key]

            catalog['lastUpdate'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_catalog(catalog)
            return {"message": "User updated successfully"}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def delete_user(self):
        data = cherrypy.request.json
        try:
            catalog = load_catalog()
            users = catalog['users']
            user = next((user for user in users if user['username'] == data['username'] and user['password'] == data['password']), None)

            if not user:
                return {"error": "Invalid username or password"}

            users.remove(user)
            catalog['lastUpdate'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_catalog(catalog)
            return {"message": "User deleted successfully"}
        except Exception as e:
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def read_user(self):
        data = cherrypy.request.json
        try:
            catalog = load_catalog()
            user = next((user for user in catalog['users'] if user['username'] == data['username']), None)
            if not user:
                return {"error": "User not found"}
            return user
        except Exception as e:
            return {"error": str(e)}


class Root(object):
    @cherrypy.expose
    def index(self):
        with open('index.html') as f:
            return f.read()


if __name__ == '__main__':
    conf = {
        '/': {
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static'
        }
    }

    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8080,
        'log.screen': True
    })

    cherrypy.tree.mount(Root(), '/', conf)
    cherrypy.tree.mount(UserService(), '/user')

    cherrypy.engine.start()
    cherrypy.engine.block()
