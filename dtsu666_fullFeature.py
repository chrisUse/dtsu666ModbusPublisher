#!/usr/bin/env python3
import time
import minimalmodbus
import serial
import struct
import paho.mqtt.client as mqtt
import json
import traceback
import warnings
import os

# Suppress MQTT deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="paho.mqtt.client")

# -------------------------
# CONFIGURATION FROM ENVIRONMENT VARIABLES
# -------------------------
MODBUS_PORT  = os.getenv('MODBUS_PORT', '/dev/ttyACM0')
MODBUS_SLAVE = int(os.getenv('MODBUS_SLAVE', '1'))
BAUDRATE     = int(os.getenv('BAUDRATE', '9600'))
PARITY       = serial.PARITY_NONE
STOPBITS     = 1
BYTESIZE     = 8
TIMEOUT      = float(os.getenv('TIMEOUT', '1.0'))

MQTT_BROKER  = os.getenv('MQTT_BROKER', '192.168.10.63')
MQTT_PORT    = int(os.getenv('MQTT_PORT', '1882'))
MQTT_USER    = os.getenv('MQTT_USER', 'user1')
MQTT_PASS    = os.getenv('MQTT_PASS', 'user1')
MQTT_PREFIX  = os.getenv('MQTT_PREFIX', 'chint/dtsu666')

DEVICE_NAME  = os.getenv('DEVICE_NAME', 'Chint DTSU666')
DEVICE_ID    = os.getenv('DEVICE_ID', 'dtsu666_meter')

MEASUREMENT_INTERVAL = int(os.getenv('MEASUREMENT_INTERVAL', '5'))

print(f"Configuration loaded:")
print(f"  Modbus: {MODBUS_PORT} @ {BAUDRATE} baud, Slave {MODBUS_SLAVE}")
print(f"  MQTT: {MQTT_BROKER}:{MQTT_PORT} as {MQTT_USER}")
print(f"  Device: {DEVICE_NAME} ({DEVICE_ID})")
print(f"  Interval: {MEASUREMENT_INTERVAL}s")

# -------------------------
# REGISTER DEFINITIONS
# -------------------------
# Based on elfabriceu/DTSU666-Modbus GitHub Repository - with original names
REGISTERS = [
    # Voltages - using original names
    {"name": "Voltage_A", "addr": 0x2006, "unit": "V", "scale": 0.1},
    {"name": "Voltage_B", "addr": 0x2008, "unit": "V", "scale": 0.1},
    {"name": "Voltage_C", "addr": 0x200A, "unit": "V", "scale": 0.1},
    # Currents - using original names
    {"name": "Current_A", "addr": 0x200C, "unit": "A", "scale": 0.001},
    {"name": "Current_B", "addr": 0x200E, "unit": "A", "scale": 0.001},
    {"name": "Current_C", "addr": 0x2010, "unit": "A", "scale": 0.001},
    # Active power - using original names
    {"name": "Power_A", "addr": 0x2014, "unit": "W", "scale": 0.1},
    {"name": "Power_B", "addr": 0x2016, "unit": "W", "scale": 0.1},
    {"name": "Power_C", "addr": 0x2018, "unit": "W", "scale": 0.1},
    {"name": "Power_Total", "addr": 0x2012, "unit": "W", "scale": 0.1},
    # Frequency - original name
    {"name": "Frequency", "addr": 0x2044, "unit": "Hz", "scale": 0.01},
    # Energy counters - original names
    {"name": "Energy_Import", "addr": 0x401E, "unit": "kWh", "scale": 1.0},
    {"name": "Energy_Export", "addr": 0x4028, "unit": "kWh", "scale": 1.0},
]

# -------------------------
# MODBUS INITIALIZATION
# -------------------------
instrument = minimalmodbus.Instrument(MODBUS_PORT, MODBUS_SLAVE)
instrument.serial.baudrate = BAUDRATE
instrument.serial.parity   = PARITY
instrument.serial.stopbits = STOPBITS
instrument.serial.bytesize = BYTESIZE
instrument.serial.timeout  = TIMEOUT
instrument.mode = minimalmodbus.MODE_RTU

# -------------------------
# MQTT INITIALIZATION
# -------------------------
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

def on_connect(client, userdata, flags, rc):
    print(f"MQTT connected with code: {rc}")

def on_publish(client, userdata, mid):
    pass  # Silent success

mqtt_client.on_connect = on_connect
mqtt_client.on_publish = on_publish
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

# -------------------------
# FUNCTIONS
# -------------------------
def read_register_value(addr, data_type):
    """
    Reads float register with the correct minimalmodbus read_float() method.
    Based on the proven elfabriceu/DTSU666-Modbus implementation.
    """
    try:
        # Use the built-in read_float() function of minimalmodbus
        # This handles the byte order automatically correctly
        float_value = instrument.read_float(addr, functioncode=3)
        
        print(f"DEBUG {hex(addr)}: Float={float_value:.3f}")
        return float_value
            
    except Exception as e:
        print(f"Error reading register {hex(addr)}: {e}")
        return None

def read_float_inverse(addr):
    """
    Old float function - no longer used.
    Kept only for compatibility.
    """
    return None

def publish_discovery():
    """Home Assistant MQTT Discovery Payloads"""
    for reg in REGISTERS:
        sensor_id = reg["name"].lower()
        topic_config = f"homeassistant/sensor/{DEVICE_ID}/{sensor_id}/config"
        state_topic = f"{MQTT_PREFIX}/{reg['name']}"
        payload = {
            "name": reg["name"].replace("_", " "),
            "state_topic": state_topic,
            "unit_of_measurement": reg["unit"],
            "unique_id": f"{DEVICE_ID}_{sensor_id}",
            "device": {
                "identifiers": [DEVICE_ID],
                "name": DEVICE_NAME,
                "model": "DTSU666",
                "manufacturer": "Chint"
            }
        }
        mqtt_client.publish(topic_config, json.dumps(payload), retain=True)

# -------------------------
# MAIN LOOP
# -------------------------
def main():
    publish_discovery()
    print("Starting DTSU666 Reader...")
    print("Waiting for first measurement...\n")
    
    while True:
        print(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        successful_reads = 0
        
        for reg in REGISTERS:
            try:
                # Read float value directly (without separate scaling factor)
                float_value = read_register_value(reg["addr"], None)
                if float_value is None:
                    print(f"{reg['name']}: Error reading")
                    continue
                
                # Float value already correctly scaled from device
                final_value = float_value * reg["scale"]
                
                # Round to sensible decimal places depending on unit
                if reg["unit"] == "V":
                    final_value = round(final_value, 1)  # 1 decimal place for volts
                elif reg["unit"] == "A":
                    final_value = round(final_value, 3)  # 3 decimal places for amperes
                elif reg["unit"] == "W":
                    final_value = round(final_value, 1)  # 1 decimal place for watts
                elif reg["unit"] == "Hz":
                    final_value = round(final_value, 2)  # 2 decimal places for frequency
                elif reg["unit"] == "kWh":
                    final_value = round(final_value, 3)  # 3 decimal places for energy
                
                # Extended plausibility check
                if reg["unit"] == "V" and (final_value < 0 or final_value > 1000):
                    print(f"{reg['name']}: Implausible ({final_value:.3f} V)")
                    continue
                elif reg["unit"] == "A" and (final_value < 0 or final_value > 1000):
                    print(f"{reg['name']}: Implausible ({final_value:.3f} A)")
                    continue
                elif reg["unit"] == "Hz" and (final_value < 40 or final_value > 70):
                    print(f"{reg['name']}: Implausible ({final_value:.3f} Hz)")
                    continue
                elif reg["unit"] == "W" and abs(final_value) > 50000:
                    print(f"{reg['name']}: Implausible ({final_value:.3f} W)")
                    continue
                
                # MQTT Publishing with rounded values
                topic = f"{MQTT_PREFIX}/{reg['name']}"
                mqtt_client.publish(topic, final_value)
                print(f"{reg['name']}: {final_value} {reg['unit']}")
                successful_reads += 1
                
            except Exception as e:
                print(f"{reg['name']}: Exception - {e}")
                traceback.print_exc()
        
        print(f"Successfully read: {successful_reads}/{len(REGISTERS)}")
        mqtt_client.loop()
        time.sleep(MEASUREMENT_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Terminated by user")

