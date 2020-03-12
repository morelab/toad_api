from os import path
import configparser

config = configparser.ConfigParser()
config.read(path.join(path.dirname(__file__), "config.ini"))

server_config = config["SERVER"]
mqtt_config = config["MQTT"]


# API server configuration
SERVER_IP = server_config["SERVER_IP"]
SERVER_PORT = int(server_config["SERVER_PORT"])

# API server's MQTT client configuration
MQTT_BROKER_IP = mqtt_config["MQTT_BROKER_IP"]
MQTT_RESPONSE_TIMEOUT = int(mqtt_config["MQTT_RESPONSE_TIMEOUT"])
