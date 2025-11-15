#!/usr/bin/env python3
import time
import minimalmodbus
import serial
import struct
import paho.mqtt.client as mqtt
import json
import traceback
import warnings

# Unterdrücke MQTT Deprecation Warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="paho.mqtt.client")

# -------------------------
# KONFIGURATION
# -------------------------
MODBUS_PORT  = '/dev/ttyACM0'
MODBUS_SLAVE = 1
BAUDRATE     = 9600
PARITY       = serial.PARITY_NONE
STOPBITS     = 1
BYTESIZE     = 8
TIMEOUT      = 1.0

MQTT_BROKER  = '192.168.10.63'
MQTT_PORT    = 1882
MQTT_USER    = 'user1'
MQTT_PASS    = 'user1'
MQTT_PREFIX  = 'chint/dtsu666'

DEVICE_NAME  = "Chint DTSU666"
DEVICE_ID    = "dtsu666_meter"

# -------------------------
# REGISTER DEFINITIONEN
# -------------------------
# Basierend auf elfabriceu/DTSU666-Modbus GitHub Repository - aber mit ursprünglichen Namen
REGISTERS = [
    # Spannungen - verwende ursprüngliche Namen
    {"name": "Voltage_A", "addr": 0x2006, "unit": "V", "scale": 0.1},
    {"name": "Voltage_B", "addr": 0x2008, "unit": "V", "scale": 0.1},
    {"name": "Voltage_C", "addr": 0x200A, "unit": "V", "scale": 0.1},
    # Ströme - verwende ursprüngliche Namen
    {"name": "Current_A", "addr": 0x200C, "unit": "A", "scale": 0.001},
    {"name": "Current_B", "addr": 0x200E, "unit": "A", "scale": 0.001},
    {"name": "Current_C", "addr": 0x2010, "unit": "A", "scale": 0.001},
    # Wirkleistung - verwende ursprüngliche Namen
    {"name": "Power_A", "addr": 0x2014, "unit": "W", "scale": 0.1},
    {"name": "Power_B", "addr": 0x2016, "unit": "W", "scale": 0.1},
    {"name": "Power_C", "addr": 0x2018, "unit": "W", "scale": 0.1},
    {"name": "Power_Total", "addr": 0x2012, "unit": "W", "scale": 0.1},
    # Frequenz - ursprünglicher Name
    {"name": "Frequency", "addr": 0x2044, "unit": "Hz", "scale": 0.01},
    # Energiezähler - ursprüngliche Namen
    {"name": "Energy_Import", "addr": 0x401E, "unit": "kWh", "scale": 1.0},
    {"name": "Energy_Export", "addr": 0x4028, "unit": "kWh", "scale": 1.0},
]

# -------------------------
# MODBUS INIT
# -------------------------
instrument = minimalmodbus.Instrument(MODBUS_PORT, MODBUS_SLAVE)
instrument.serial.baudrate = BAUDRATE
instrument.serial.parity   = PARITY
instrument.serial.stopbits = STOPBITS
instrument.serial.bytesize = BYTESIZE
instrument.serial.timeout  = TIMEOUT
instrument.mode = minimalmodbus.MODE_RTU

# -------------------------
# MQTT INIT
# -------------------------
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

def on_connect(client, userdata, flags, rc):
    print(f"MQTT verbunden mit Code: {rc}")

def on_publish(client, userdata, mid):
    pass  # Stiller Erfolg

mqtt_client.on_connect = on_connect
mqtt_client.on_publish = on_publish
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

# -------------------------
# FUNKTIONEN
# -------------------------
# -------------------------
# FUNKTIONEN
# -------------------------
def read_register_value(addr, data_type):
    """
    Liest Float-Register mit der korrekten minimalmodbus read_float() Methode.
    Basierend auf der bewährten elfabriceu/DTSU666-Modbus Implementation.
    """
    try:
        # Verwende die eingebaute read_float() Funktion von minimalmodbus
        # Diese handhabt die Byte-Reihenfolge automatisch korrekt
        float_value = instrument.read_float(addr, functioncode=3)
        
        print(f"DEBUG {hex(addr)}: Float={float_value:.3f}")
        return float_value
            
    except Exception as e:
        print(f"Fehler beim Lesen Register {hex(addr)}: {e}")
        return None

def read_float_inverse(addr):
    """
    Alte Float-Funktion - wird nicht mehr verwendet.
    Nur zur Kompatibilität beibehalten.
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
    print("Starte DTSU666 Reader...")
    print("Warte auf erste Messung...\n")
    
    while True:
        print(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        successful_reads = 0
        
        for reg in REGISTERS:
            try:
                # Lese Float-Wert direkt (ohne separaten Skalierungsfaktor)
                float_value = read_register_value(reg["addr"], None)
                if float_value is None:
                    print(f"{reg['name']}: Fehler beim Lesen")
                    continue
                
                # Float-Wert bereits korrekt skaliert aus dem Gerät
                final_value = float_value * reg["scale"]
                
                # Erweiterte Plausibilitätsprüfung
                if reg["unit"] == "V" and (final_value < 0 or final_value > 1000):
                    print(f"{reg['name']}: Unplausibel ({final_value:.3f} V)")
                    continue
                elif reg["unit"] == "A" and (final_value < 0 or final_value > 1000):
                    print(f"{reg['name']}: Unplausibel ({final_value:.3f} A)")
                    continue
                elif reg["unit"] == "Hz" and (final_value < 40 or final_value > 70):
                    print(f"{reg['name']}: Unplausibel ({final_value:.3f} Hz)")
                    continue
                elif reg["unit"] == "W" and abs(final_value) > 50000:
                    print(f"{reg['name']}: Unplausibel ({final_value:.3f} W)")
                    continue
                
                # MQTT Publishing
                topic = f"{MQTT_PREFIX}/{reg['name']}"
                mqtt_client.publish(topic, final_value)
                print(f"{reg['name']}: {final_value:.3f} {reg['unit']}")
                successful_reads += 1
                
            except Exception as e:
                print(f"{reg['name']}: Ausnahme - {e}")
                traceback.print_exc()
        
        print(f"Erfolgreich gelesen: {successful_reads}/{len(REGISTERS)}")
        mqtt_client.loop()
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Beendet durch Benutzer")

