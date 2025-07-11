#!/usr/bin/env python3
"""
Analyze the device info JSON to discover additional data points
"""

import json

# Load the full household data
with open('full_household_data.json', 'r') as f:
    data = json.load(f)

# Extract device info from first pet with collar
device_info = data['data']['currentUser']['userHouseholds'][0]['household']['pets'][0]['device']['info']

print("=== Device Info Analysis ===\n")

print("## Battery Information")
print(f"- Battery Percent: {device_info['batteryPercent']}%")
print(f"- Battery Health: {device_info['bq27421Info']['batteryHealthPercent']}%")
print(f"- Battery Health Status: {device_info['bq27421Info']['batteryHealthStatus']}")
print(f"- Battery Voltage: {device_info['bq27421Info']['batteryVoltageMv']} mV")
print(f"- Battery Temperature: {device_info['bq27421Info']['temperatureK']} K ({device_info['bq27421Info']['temperatureK'] - 273.15:.1f}°C)")
print(f"- Remaining Capacity: {device_info['bq27421Info']['batteryRemainingCapacityMah']} mAh")
print(f"- Full Charge Capacity: {device_info['bq27421Info']['batteryFullChargeCapacityMah']} mAh")
print(f"- Design Capacity: {device_info['bq27421Info']['batteryDesignCapacityMah']} mAh")

print("\n## Firmware Information")
print(f"- Build ID: {device_info['buildId']}")
print(f"- NRF52 App Version: {device_info['manifest']['nrf52App']['major']}.{device_info['manifest']['nrf52App']['minor']}.{device_info['manifest']['nrf52App']['patch']}")
print(f"- NRF52 Bootloader: {device_info['manifest']['nrf52Bl']['major']}.{device_info['manifest']['nrf52Bl']['minor']}.{device_info['manifest']['nrf52Bl']['patch']}")
print(f"- NRF9160 Version: {device_info['manifest']['nrf9160']['major']}.{device_info['manifest']['nrf9160']['label']}")
print(f"- DA16200 Version: {device_info['manifest']['da16200']['minor']}")

print("\n## Connection Information")
print(f"- WiFi Networks: {', '.join(device_info['wifiNetworkNames'])}")
print(f"- BLE Connection Status: {device_info['bleConnectionStats']['bleConnectionStatus']}")
print(f"- BLE RSSI: {device_info['bleConnectionStats']['rssi']} dBm")
print(f"- BLE MTU: {device_info['bleConnectionStats']['mtu']}")
print(f"- Uptime: {device_info['uptime']} seconds ({device_info['uptime'] / 86400:.1f} days)")

print("\n## WiFi Statistics")
for ssid_stat in device_info['wifiStats']['ssidStats']:
    if 'scanned' in ssid_stat:
        print(f"- {ssid_stat['ssid']}: {ssid_stat.get('scanned', 0)} scans, {ssid_stat.get('connectSuccess', 0)} successful connections")

print("\n## Device Statistics")
stats = device_info['deviceStats']['fields']
print(f"- GNSS Success Rate: {stats['gnssSuccessCount']}/{stats['gnssSuccessCount'] + stats['gnssFailureCount']} ({100 * stats['gnssSuccessCount'] / (stats['gnssSuccessCount'] + stats['gnssFailureCount']):.1f}%)")
print("- Total Distance Tracked: Not available in current stats")
print(f"- LED Usage: {stats['ledPowerOnTime']} seconds total")
print(f"- BLE Connections: {stats['bleConnCount']}")
print(f"- WiFi Disconnects: {stats['wifiDisconnect']}")
print(f"- Modem Registrations: {stats['modemRegCount']}")
print(f"- Submission Reports: {stats['submissionReportCount']}")

print("\n## GPS Validity")
print(f"- GPS Valid Until: {device_info['lleStatus']['gpsValidity']['startYear']}-{device_info['lleStatus']['gpsValidity']['startMonth']:02d}-{device_info['lleStatus']['gpsValidity']['startDay']:02d} + {device_info['lleStatus']['gpsValidity']['validityDays']} days")
print(f"- GLONASS Valid Until: {device_info['lleStatus']['glonassValidity']['startYear']}-{device_info['lleStatus']['glonassValidity']['startMonth']:02d}-{device_info['lleStatus']['glonassValidity']['startDay']:02d} + {device_info['lleStatus']['glonassValidity']['validityDays']} days")
if 'startYear' in device_info['lleStatus']['galileoValidity']:
    print(f"- Galileo Valid Until: {device_info['lleStatus']['galileoValidity']['startYear']}-{device_info['lleStatus']['galileoValidity']['startMonth']:02d}-{device_info['lleStatus']['galileoValidity']['startDay']:02d} + {device_info['lleStatus']['galileoValidity']['validityDays']} days")

print("\n## Additional Features Not Currently Exposed")
print("1. Battery health percentage and status")
print("2. Battery temperature monitoring")
print("3. Battery capacity tracking (design vs actual)")
print("4. Detailed firmware version information")
print("5. WiFi network list and connection statistics")
print("6. BLE connection quality (RSSI)")
print("7. Device uptime tracking")
print("8. GPS/GLONASS/Galileo validity dates")
print("9. Detailed connection statistics per network")
print("10. LED usage statistics")

# Check place information
pet = data['data']['currentUser']['userHouseholds'][0]['household']['pets'][0]
print("\n## Current Activity Information")
print(f"- Pet Name: {pet['name']}")
print(f"- Instagram Handle: {pet.get('instagramHandle', 'Not set')}")

# Check base station additional info
bases = data['data']['currentUser']['userHouseholds'][0]['household']['bases']
print("\n## Base Station Information")
for base in bases:
    print(f"\n- Base: {base['name']} ({base['baseId']})")
    print(f"  - Online: {base['online']} ({base['onlineQuality']})")
    print(f"  - Network: {base['networkName']}")
    print(f"  - Last Update: {base['infoLastUpdated']}")
    print(f"  - Location: {base['position']['latitude']}, {base['position']['longitude']}")