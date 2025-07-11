# TryFi API Discovery Report

## Executive Summary

This report documents the exploration of the TryFi GraphQL API to identify additional features and data not currently exposed in the Home Assistant integration. While the API exploration revealed that TryFi has limited their GraphQL API access (blocking introspection and many extended queries), analysis of the existing data responses uncovered several valuable features that could be added to enhance the integration.

## Key Discoveries

### 1. **Device/Collar Advanced Information**

The device info structure contains extensive data not currently exposed:

#### Battery Health Monitoring
- **Battery Health Percentage**: 97% (actual battery health vs design capacity)
- **Battery Health Status**: "SOH_INITIAL_READY" (state of health indicator)
- **Battery Voltage**: 4190 mV (useful for precise monitoring)
- **Battery Temperature**: 30.4°C (important for battery longevity)
- **Capacity Tracking**:
  - Design Capacity: 265 mAh
  - Current Full Capacity: 261 mAh
  - Remaining Capacity: 240 mAh
- **Battery Resistance Profile**: Array of resistance values for battery diagnostics

#### Firmware & Hardware Details
- **Detailed Firmware Versions**:
  - NRF52 App: 4.16.61
  - NRF52 Bootloader: 4.15.3
  - NRF9160 Modem: 1.3.1
  - WiFi Module: v69
- **Device Uptime**: 10.3 days (useful for stability monitoring)
- **Capability Flags**: Indicates device features

#### Connection Analytics
- **WiFi Network Management**:
  - List of configured networks: ["MAVeCap", "BeachHouse116", "RLC_Shonehaus_5GHz", "wirelessx"]
  - Connection statistics per network (attempts, successes, failures)
- **BLE Connection Quality**:
  - RSSI: -59 dBm (signal strength)
  - Connection status: "CONNECTED_FULLY_ATTACHED"
  - MTU size: 247 bytes
- **Cellular/LTE Statistics**:
  - Modem registrations: 14
  - Connection time tracking

#### GPS System Status
- **Multi-constellation Support**:
  - GPS validity: 2025-06-16 + 3 days
  - GLONASS validity: 2025-06-16 + 3 days  
  - Galileo validity: 2023-03-09 + 3 days
- **GNSS Performance**: 88.9% success rate (24/27 fixes)

### 2. **Activity & Rest Data Enhancements**

#### Rest/Sleep Tracking
- Daily, weekly, and monthly sleep duration (currently retrieved but not exposed)
- Daily, weekly, and monthly nap duration
- Sleep vs nap differentiation

#### Place Information
- When pet is resting, location includes place name (e.g., "Home")
- Place address information available

#### Activity Type
- Current activity type (OngoingWalk vs OngoingRest)
- Area name during activities

### 3. **Base Station Features**

- **Connection Quality**: "HEALTHY" vs "UNHEALTHY" status
- **Network Information**: WiFi network name for each base
- **Last Update Time**: Timestamp of last base station check-in
- **Custom Names**: Bases can have custom names (e.g., "Adam Office", "Diane Travel")

### 4. **Pet Profile Enhancements**

- **Photo URLs**: Direct links to pet photos
- **Instagram Handle**: Social media integration field
- **Multiple Photos**: Photo feed with multiple images per pet

## Recommended Integration Enhancements

### High Priority Features

1. **Enhanced Battery Monitoring**
   - Add battery health percentage sensor
   - Add battery voltage sensor
   - Add battery temperature sensor (with high temp alerts)
   - Add battery capacity degradation tracking

2. **Rest/Sleep Sensors**
   - Add daily/weekly/monthly sleep duration sensors
   - Add daily/weekly/monthly nap duration sensors
   - Add sleep quality metrics (sleep vs nap ratio)

3. **Activity Type & Location**
   - Add activity type sensor (walking/resting)
   - Add current place name sensor
   - Add area name sensor

4. **Connection Quality**
   - Add BLE RSSI sensor for connection quality
   - Add base station health status
   - Add device uptime sensor

### Medium Priority Features

1. **Device Information**
   - Add firmware version sensors
   - Add WiFi network list attribute
   - Add GPS validity date tracking

2. **Calculated Sensors**
   - Pet age calculation from birthdate
   - Goal achievement percentage (daily/weekly/monthly)
   - Activity trends (comparing periods)

3. **Base Station Enhancements**
   - Expose base station network name
   - Add last seen timestamp
   - Support custom base names

### Low Priority Features

1. **Photo Integration**
   - Use pet photo as entity picture
   - Expose photo URLs as attributes

2. **Social Features**
   - Instagram handle attribute

3. **Advanced Diagnostics**
   - Connection statistics per WiFi network
   - GNSS success rate tracking
   - LED usage statistics

## Implementation Notes

### Data Already Available
All the features listed above can be implemented using data that's already being retrieved by the current integration. The main work involves:
1. Parsing additional fields from existing API responses
2. Creating new sensor entities
3. Adding appropriate device classes and units

### Example Sensor Additions

```python
# Battery Health Sensor
battery_health = device_info['bq27421Info']['batteryHealthPercent']

# Battery Temperature Sensor  
battery_temp_k = device_info['bq27421Info']['temperatureK']
battery_temp_c = (battery_temp_k / 10) - 273.15  # Note: temp is in deciKelvin

# Sleep Duration Sensors
daily_sleep = pet.dailySleep  # Already available in fiPet
daily_nap = pet.dailyNap

# Activity Type Sensor
activity_type = pet.activityType  # "OngoingWalk" or "OngoingRest"

# Place Name Sensor
current_place = pet.currPlaceName  # e.g., "Home"
```

## Limitations & Constraints

1. **No Historical Data Access**: The API only provides current state and period summaries
2. **No Geofencing**: No evidence of geofencing or zone management in the API
3. **Limited Notifications**: Only basic on/off for news notifications
4. **No Real-time Tracking**: No websocket or streaming data available

## Conclusion

While the TryFi API is more limited than initially expected, there are numerous valuable features already available in the API responses that aren't exposed in the Home Assistant integration. The highest value additions would be:

1. **Battery health monitoring** - Critical for maintaining collar reliability
2. **Sleep/rest tracking** - Valuable health metrics for pet owners
3. **Enhanced location context** - Place names and activity types
4. **Connection quality monitoring** - For troubleshooting and reliability

These enhancements would significantly improve the user experience without requiring any API changes from TryFi.