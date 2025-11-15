# DTSU666 Modbus to MQTT Reader (Docker)

This Docker setup reads data from the Chint DTSU666 power meter via Modbus RTU and publishes it via MQTT with Home Assistant Auto-Discovery.

## 🚀 Quick Start

1. **Configure** in `.env`:
   ```bash
   # Modbus adapter (usually /dev/ttyUSB0 or /dev/ttyACM0)
   MODBUS_PORT=/dev/ttyACM0
   
   # MQTT Broker settings
   MQTT_BROKER=192.168.1.100
   MQTT_PORT=1883
   MQTT_USER=your_user
   MQTT_PASS=your_password
   ```

2. **Start Docker container**:
   ```bash
   docker-compose up -d
   ```

3. **Check logs**:
   ```bash
   docker-compose logs -f dtsu666-reader
   ```

## 📋 Complete .env Configuration

```bash
# MODBUS Configuration
MODBUS_PORT=/dev/ttyACM0      # USB-RS485 Adapter
MODBUS_SLAVE=1                # Device ID of the DTSU666
BAUDRATE=9600                 # Standard Baudrate
TIMEOUT=1.0                   # Timeout in seconds

# MQTT Configuration  
MQTT_BROKER=192.168.10.63     # IP of your MQTT Broker
MQTT_PORT=1883                # MQTT Port (default: 1883)
MQTT_USER=user1               # MQTT Username
MQTT_PASS=user1               # MQTT Password
MQTT_PREFIX=chint/dtsu666     # Topic prefix

# Device Configuration
DEVICE_NAME=Chint DTSU666     # Name in Home Assistant
DEVICE_ID=dtsu666_meter       # Unique Device ID

# Measurement interval
MEASUREMENT_INTERVAL=5        # Seconds between measurements
```

## 🔧 Raspberry Pi Setup

1. **Identify USB-RS485 adapter**:
   ```bash
   dmesg | grep tty
   ls -la /dev/tty*
   ```

2. **Set device permissions**:
   ```bash
   sudo usermod -a -G dialout $USER
   # Relogin required!
   ```

3. **Install Docker & Docker Compose**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   sudo apt install docker-compose-plugin
   ```

## 📊 Transmitted Measurements

| Sensor | Unit | Topic | Description |
|--------|------|-------|-------------|
| `Voltage_A/B/C` | V | `chint/dtsu666/Voltage_A` | Phase voltages |
| `Current_A/B/C` | A | `chint/dtsu666/Current_A` | Phase currents |
| `Power_A/B/C` | W | `chint/dtsu666/Power_A` | Phase power |
| `Power_Total` | W | `chint/dtsu666/Power_Total` | Total active power |
| `Frequency` | Hz | `chint/dtsu666/Frequency` | Grid frequency |
| `Energy_Import` | kWh | `chint/dtsu666/Energy_Import` | Imported energy |
| `Energy_Export` | kWh | `chint/dtsu666/Energy_Export` | Exported energy |

## 🏠 Home Assistant Integration

The sensors appear automatically in Home Assistant thanks to MQTT Auto-Discovery:
- Device: `Chint DTSU666` 
- Entity IDs: `sensor.chint_dtsu666_voltage_a`, etc.
- Update interval: Configurable via `MEASUREMENT_INTERVAL`

### Dashboard Configuration
The `homeassistant/` folder contains configuration files to create a dashboard:
- **Dashboard YAML**: Ready-to-import dashboard configuration
- **Entity configurations**: Custom sensor configurations if needed
- **Lovelace cards**: Pre-configured cards for energy monitoring

Simply copy the files from the `homeassistant/` directory to your Home Assistant configuration.

## 🛠 Troubleshooting

**Container won't start:**
```bash
# Check logs
docker-compose logs dtsu666-reader

# Check device permissions
ls -la /dev/ttyACM0
groups $USER
```

**No MQTT connection:**
```bash
# Test MQTT broker
mosquitto_pub -h 192.168.10.63 -p 1883 -u user1 -P user1 -t test -m "hello"
```

**Modbus errors:**
```bash
# Show USB devices
lsusb
dmesg | tail

# Check for other processes
sudo lsof /dev/ttyACM0
```

## 🔄 Updates

```bash
# Stop container and build new image
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 📈 Monitoring

**Check health status:**
```bash
docker ps
docker inspect dtsu666-modbus-reader | grep Health
```

**Monitor performance:**
```bash
docker stats dtsu666-modbus-reader
```