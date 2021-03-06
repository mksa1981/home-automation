import re
import platform
import sys
from typing import List, Tuple
from threading import Timer
import time
import json
from bluepy.btle import Scanner, DefaultDelegate
from btlewrap import available_backends, BluepyBackend, GatttoolBackend, PygattBackend, BluetoothBackendException
from mitemp_bt.mitemp_bt_poller import MiTempBtPoller, MI_TEMPERATURE, MI_HUMIDITY, MI_BATTERY
import paho.mqtt.client as mqtt
from xioami_sensor_poller.config import settings

# Default values
MI_DEVICE_NAME = "MJ_HT_V1"
BLE_SCAN_TIMEOUT = 60.0
BLE_POLLING_INTERNAL = 60
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
MQTT_TOPIC_PREFIX = "home/xioami_sensor/"

# Scan for for MJ_HT_V1 BLE device. Return list of devices found
def scan(timeout=BLE_SCAN_TIMEOUT):
    devices = []
    all_devices = BluepyBackend.scan_for_devices(timeout)
    for device in all_devices:
        if device[1] == MI_DEVICE_NAME:
            devices.append(device)
    print('Found {} devices:'.format(len(devices)))
    return devices

# Initialize MQTT connection. Return MQTT client
def init_mqtt_connection():
    mqtt_server=settings.mqtt_server
    mqtt_user=settings.mqtt_user
    mqtt_pass=settings.mqtt_pass
    mqtt_port=settings.mqtt_port
    mqtt_timeout=settings.mqtt_timeout
    client = mqtt.Client()
    client.username_pw_set(mqtt_user,mqtt_pass)
    client.connect(mqtt_server, mqtt_port, mqtt_timeout)
    return client
    

def fetch_sensor_data_loop(pollers,mqtt_client):
    mqtt_topic_prefix = settings.mqtt_topic_prefix
    # Continually loop through pollers and submit data every BLE_POLLING_INTERVAL seconds
    try:
        while True:
            for poller in pollers:
                mac = poller[0]
                poll = poller[1]
                timestamp = time.strftime(DATETIME_FORMAT)
                temp = poll.parameter_value(MI_TEMPERATURE)
                humidity = poll.parameter_value(MI_HUMIDITY)
                battery_level = poll.parameter_value(MI_BATTERY)
                topic = mqtt_topic_prefix + mac
                payload = json.dumps({ 'Time': timestamp, 'Temp': temp, 'Humidity': humidity, 'Battery': battery_level})
                print("Topic:" + topic + "-" + payload)
                res=mqtt_client.publish(topic=topic, payload=payload)
                print (str(res[0]) + "," + str(res[1]))
            sleep_time=BLE_POLLING_INTERNAL - time.time() % BLE_POLLING_INTERNAL
            print("Sleep for:" + str(sleep_time))
            time.sleep(sleep_time)
    except:
        print("Unexpected error:", sys.exc_info()[0])


def main():
    #Setup MQTT connection
    mqtt_client = init_mqtt_connection()

    
    # Scan for Xiaomi temp devices
    devices = scan()

    # Tuple consisting of (device_mac, poller)
    pollers = []
    # Create poller for each device
    for device in devices:
        poller = MiTempBtPoller(device[0], BluepyBackend, 20.0)
        pollers.append((device[0],poller))

    # Continually loop through pollers and submit data every BLE_POLLING_INTERVAL seconds
    fetch_sensor_data_loop(pollers, mqtt_client)

if __name__ == "__main__":
    main()
