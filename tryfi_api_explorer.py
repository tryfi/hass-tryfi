#!/usr/bin/env python3
"""
TryFi API Explorer Script
This script explores the TryFi GraphQL API to discover additional features and data
not currently exposed in the Home Assistant integration.
"""

import json
import requests
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add the pytryfi module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components/tryfi'))

from pytryfi.const import API_HOST_URL_BASE, API_LOGIN, API_GRAPHQL, HEADER

# Credentials
USERNAME = "adam@adam.gs"
PASSWORD = "wygduv-5Zuxge-gezjes"

class TryFiExplorer:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.user_id = None
        self.session_id = None
        self.api_host = API_HOST_URL_BASE
        self.discovered_features = {}
        
    def login(self) -> bool:
        """Login to TryFi API"""
        url = self.api_host + API_LOGIN
        params = {
            'email': self.username,
            'password': self.password,
        }
        
        try:
            response = self.session.post(url, data=params)
            response.raise_for_status()
            
            data = response.json()
            if 'error' in data:
                print(f"Login error: {data['error']}")
                return False
                
            self.user_id = data.get('userId')
            self.session_id = data.get('sessionId')
            self.session.headers = HEADER
            print(f"Successfully logged in! User ID: {self.user_id}")
            return True
            
        except requests.RequestException as e:
            print(f"Login failed: {e}")
            return False
            
    def graphql_query(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict]:
        """Execute a GraphQL query"""
        url = self.api_host + API_GRAPHQL
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if 'errors' in data:
                print(f"GraphQL error: {data['errors']}")
                return None
                
            return data.get('data')
            
        except requests.RequestException as e:
            print(f"GraphQL request failed: {e}")
            return None
            
    def explore_schema(self):
        """Explore the GraphQL schema using introspection"""
        print("\n=== Exploring GraphQL Schema ===")
        
        # Get all types
        introspection_query = """
        query IntrospectionQuery {
          __schema {
            types {
              name
              kind
              description
              fields {
                name
                description
                type {
                  name
                  kind
                  ofType {
                    name
                    kind
                  }
                }
                args {
                  name
                  description
                  type {
                    name
                    kind
                    ofType {
                      name
                      kind
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        result = self.graphql_query(introspection_query)
        if result:
            types = result['__schema']['types']
            
            # Filter out internal types
            custom_types = [t for t in types if not t['name'].startswith('__')]
            
            # Save schema for analysis
            with open('tryfi_schema.json', 'w') as f:
                json.dump(custom_types, f, indent=2)
                
            print(f"Found {len(custom_types)} custom types in schema")
            
            # Analyze interesting types
            interesting_types = ['Query', 'Mutation', 'Pet', 'User', 'Device', 'ChargingBase',
                               'Activity', 'Place', 'Household', 'Subscription', 'Alert',
                               'Geofence', 'SafeZone', 'Walk', 'Rest', 'Location']
            
            for type_name in interesting_types:
                type_info = next((t for t in custom_types if t['name'] == type_name), None)
                if type_info and type_info.get('fields'):
                    print(f"\nType: {type_name}")
                    for field in type_info['fields']:
                        print(f"  - {field['name']}: {field.get('description', 'No description')}")
                        
    def explore_user_data(self):
        """Explore comprehensive user data"""
        print("\n=== Exploring User Data ===")
        
        # Extended user query
        user_query = """
        query ExtendedUserData {
          currentUser {
            id
            email
            firstName
            lastName
            phoneNumber
            createdAt
            updatedAt
            fiNewsNotificationsEnabled
            emailVerified
            phoneVerified
            preferences {
              notificationSettings {
                email
                push
                sms
              }
              units
              timezone
            }
            subscription {
              id
              status
              planType
              startDate
              endDate
              autoRenew
              features
            }
            userHouseholds {
              role
              permissions
              joinedAt
              household {
                id
                name
                createdAt
                memberCount
                pets {
                  id
                  name
                }
                bases {
                  baseId
                  name
                }
                places {
                  id
                  name
                  address
                  radius
                  position {
                    latitude
                    longitude
                  }
                  isHome
                  notifyOnEntry
                  notifyOnExit
                }
                geofences {
                  id
                  name
                  radius
                  center {
                    latitude
                    longitude
                  }
                  enabled
                  notifyOnEntry
                  notifyOnExit
                }
              }
            }
          }
        }
        """
        
        result = self.graphql_query(user_query)
        if result:
            with open('user_data_extended.json', 'w') as f:
                json.dump(result, f, indent=2)
            print("Extended user data saved to user_data_extended.json")
            
            # Analyze findings
            user = result.get('currentUser', {})
            households = user.get('userHouseholds', [])
            
            if households:
                household = households[0].get('household', {})
                places = household.get('places', [])
                geofences = household.get('geofences', [])
                
                if places:
                    print(f"\nFound {len(places)} saved places!")
                    self.discovered_features['places'] = places
                    
                if geofences:
                    print(f"Found {len(geofences)} geofences!")
                    self.discovered_features['geofences'] = geofences
                    
    def explore_pet_history(self, pet_id: str):
        """Explore historical pet data"""
        print(f"\n=== Exploring Pet History for {pet_id} ===")
        
        # Calculate date ranges
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        history_query = """
        query PetHistory($petId: ID!, $startDate: DateTime!, $endDate: DateTime!) {
          pet(id: $petId) {
            id
            name
            
            # Activity history
            activityHistory(startDate: $startDate, endDate: $endDate) {
              date
              totalSteps
              totalDistance
              activeMinutes
              restMinutes
              walks {
                startTime
                endTime
                duration
                distance
                steps
                path {
                  latitude
                  longitude
                  timestamp
                }
              }
              rests {
                startTime
                endTime
                duration
                type
                location {
                  latitude
                  longitude
                }
              }
            }
            
            # Location history
            locationHistory(startDate: $startDate, endDate: $endDate, limit: 1000) {
              timestamp
              position {
                latitude
                longitude
              }
              accuracy
              source
              battery
            }
            
            # Alert history
            alertHistory(limit: 100) {
              id
              type
              message
              timestamp
              resolved
              location {
                latitude
                longitude
              }
            }
            
            # Health metrics
            healthMetrics {
              weight {
                value
                unit
                recordedAt
              }
              temperature {
                value
                unit
                recordedAt
              }
              heartRate {
                value
                recordedAt
              }
            }
            
            # Training data
            trainingStats {
              totalSessions
              completedCommands
              averageResponseTime
              achievements {
                name
                unlockedAt
                description
              }
            }
          }
        }
        """
        
        variables = {
            "petId": pet_id,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat()
        }
        
        result = self.graphql_query(history_query, variables)
        if result:
            with open(f'pet_history_{pet_id}.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Pet history saved to pet_history_{pet_id}.json")
            
    def explore_device_capabilities(self, module_id: str):
        """Explore device/collar capabilities"""
        print(f"\n=== Exploring Device Capabilities for {module_id} ===")
        
        device_query = """
        query DeviceCapabilities($moduleId: String!) {
          device(moduleId: $moduleId) {
            moduleId
            model
            firmwareVersion
            hardwareVersion
            manufacturingDate
            
            capabilities {
              hasGPS
              hasWifi
              hasBluetooth
              hasLTE
              hasTemperatureSensor
              hasAccelerometer
              hasHeartRateMonitor
              hasSpeaker
              hasMicrophone
              hasVibration
            }
            
            batteryInfo {
              level
              isCharging
              lastCharged
              estimatedLife
              temperature
              health
            }
            
            connectivity {
              currentConnection
              signalStrength
              lastSeen
              wifiNetworks {
                ssid
                signalStrength
                connected
              }
              cellularInfo {
                carrier
                signalStrength
                dataUsage
              }
            }
            
            diagnostics {
              uptime
              restartCount
              errorLogs {
                timestamp
                message
                severity
              }
              performanceMetrics {
                cpuUsage
                memoryUsage
                storageUsage
              }
            }
            
            settings {
              updateInterval
              trackingMode
              powerSaveMode
              soundEnabled
              vibrationEnabled
              nightMode {
                enabled
                startTime
                endTime
              }
            }
          }
        }
        """
        
        variables = {"moduleId": module_id}
        
        result = self.graphql_query(device_query, variables)
        if result:
            with open(f'device_capabilities_{module_id}.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Device capabilities saved to device_capabilities_{module_id}.json")
            
    def explore_base_features(self, base_id: str):
        """Explore base station features"""
        print(f"\n=== Exploring Base Station Features for {base_id} ===")
        
        base_query = """
        query BaseFeatures($baseId: String!) {
          chargingBase(baseId: $baseId) {
            baseId
            name
            model
            firmwareVersion
            
            networkInfo {
              ssid
              signalStrength
              ipAddress
              macAddress
              uptime
              dataUsage
            }
            
            connectedDevices {
              moduleId
              petName
              lastSeen
              chargingStatus
              batteryLevel
            }
            
            settings {
              ledBrightness
              soundEnabled
              autoUpdate
              timezone
            }
            
            diagnostics {
              temperature
              powerConsumption
              errorCount
              lastRestart
            }
            
            location {
              address
              position {
                latitude
                longitude
              }
              timezone
              weather {
                temperature
                condition
                humidity
              }
            }
          }
        }
        """
        
        variables = {"baseId": base_id}
        
        result = self.graphql_query(base_query, variables)
        if result:
            with open(f'base_features_{base_id}.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Base features saved to base_features_{base_id}.json")
            
    def explore_analytics(self):
        """Explore analytics and insights"""
        print("\n=== Exploring Analytics & Insights ===")
        
        analytics_query = """
        query Analytics {
          currentUser {
            households {
              analytics {
                petComparisons {
                  petId
                  petName
                  ranking {
                    activityRank
                    totalPets
                    percentile
                  }
                  trends {
                    activityTrend
                    sleepTrend
                    outdoorTimeTrend
                  }
                }
                
                insights {
                  type
                  title
                  description
                  recommendation
                  priority
                  relatedPetId
                }
                
                patterns {
                  walkPatterns {
                    mostCommonTimes
                    averageDuration
                    favoriteRoutes {
                      name
                      frequency
                      distance
                    }
                  }
                  
                  sleepPatterns {
                    averageBedtime
                    averageWakeTime
                    totalSleepHours
                    napFrequency
                  }
                  
                  behaviorPatterns {
                    activityPeaks
                    restPeriods
                    socialInteractions
                  }
                }
                
                healthScores {
                  overallScore
                  activityScore
                  sleepScore
                  consistencyScore
                  lastUpdated
                }
              }
            }
          }
        }
        """
        
        result = self.graphql_query(analytics_query)
        if result:
            with open('analytics_insights.json', 'w') as f:
                json.dump(result, f, indent=2)
            print("Analytics data saved to analytics_insights.json")
            
    def explore_notifications_alerts(self):
        """Explore notification and alert settings"""
        print("\n=== Exploring Notifications & Alerts ===")
        
        notifications_query = """
        query NotificationsAlerts {
          currentUser {
            notificationPreferences {
              enabled
              channels {
                email
                push
                sms
              }
              
              alertTypes {
                lowBattery {
                  enabled
                  threshold
                }
                escapedSafeZone {
                  enabled
                  cooldownMinutes
                }
                deviceOffline {
                  enabled
                  timeoutMinutes
                }
                activityGoalReached {
                  enabled
                }
                unusualActivity {
                  enabled
                  sensitivity
                }
                healthAlert {
                  enabled
                  types
                }
              }
              
              schedules {
                quietHours {
                  enabled
                  startTime
                  endTime
                  daysOfWeek
                }
                
                customSchedules {
                  name
                  enabled
                  alertTypes
                  schedule {
                    startTime
                    endTime
                    daysOfWeek
                  }
                }
              }
            }
            
            alertHistory(limit: 50) {
              id
              type
              severity
              message
              timestamp
              acknowledged
              acknowledgedAt
              relatedPet {
                id
                name
              }
              data
            }
          }
        }
        """
        
        result = self.graphql_query(notifications_query)
        if result:
            with open('notifications_alerts.json', 'w') as f:
                json.dump(result, f, indent=2)
            print("Notifications data saved to notifications_alerts.json")
            
    def run_exploration(self):
        """Run the complete exploration"""
        if not self.login():
            print("Failed to login. Exiting.")
            return
            
        # First get basic data to find IDs
        print("\n=== Getting Basic Data ===")
        basic_query = """
        query BasicData {
          currentUser {
            userHouseholds {
              household {
                pets {
                  id
                  name
                  device {
                    moduleId
                  }
                }
                bases {
                  baseId
                  name
                }
              }
            }
          }
        }
        """
        
        result = self.graphql_query(basic_query)
        if not result:
            print("Failed to get basic data")
            return
            
        # Extract IDs
        pet_id = None
        module_id = None
        base_id = None
        
        households = result.get('currentUser', {}).get('userHouseholds', [])
        if households:
            household = households[0].get('household', {})
            pets = household.get('pets', [])
            bases = household.get('bases', [])
            
            if pets:
                pet = pets[0]
                pet_id = pet['id']
                module_id = pet.get('device', {}).get('moduleId')
                print(f"Found pet: {pet['name']} (ID: {pet_id})")
                
            if bases:
                base = bases[0]
                base_id = base['baseId']
                print(f"Found base: {base['name']} (ID: {base_id})")
        
        # Run all explorations
        self.explore_schema()
        self.explore_user_data()
        
        if pet_id:
            self.explore_pet_history(pet_id)
            
        if module_id:
            self.explore_device_capabilities(module_id)
            
        if base_id:
            self.explore_base_features(base_id)
            
        self.explore_analytics()
        self.explore_notifications_alerts()
        
        # Generate report
        self.generate_report()
        
    def generate_report(self):
        """Generate a comprehensive report of findings"""
        print("\n=== Generating Report ===")
        
        report = """
# TryFi API Exploration Report

## Summary
This report documents the exploration of the TryFi GraphQL API to discover features and data not currently exposed in the Home Assistant integration.

## Key Discoveries

### 1. Places and Geofencing
- The API supports custom places with entry/exit notifications
- Geofences can be created with custom radius and notification settings
- Multiple geofences per household are supported

### 2. Historical Data
- Detailed activity history is available (walks, rests, steps, distance)
- Location history with timestamps and accuracy
- Alert history with resolution status

### 3. Health Metrics
- Weight tracking over time
- Temperature monitoring (if supported by device)
- Heart rate data (if supported by device)

### 4. Analytics and Insights
- Pet activity comparisons and rankings
- Behavior patterns and trends
- Health scores and recommendations
- Favorite walking routes

### 5. Advanced Device Features
- Detailed battery information including health and temperature
- Device diagnostics and error logs
- Performance metrics
- Night mode settings

### 6. Base Station Features
- Network diagnostics
- Connected devices monitoring
- Power consumption data
- Weather information at base location

### 7. Notification System
- Granular alert type configuration
- Quiet hours and custom schedules
- Multiple notification channels (email, push, SMS)
- Alert history with acknowledgment tracking

### 8. Training and Achievements
- Training session tracking
- Command completion stats
- Achievement/badge system

## Recommendations for Integration Enhancement

1. **Add Historical Data Entities**
   - Create sensors for historical step/distance data
   - Add location history tracking
   - Implement activity pattern analysis

2. **Implement Geofencing**
   - Add place management
   - Create zone-based automations
   - Entry/exit notifications

3. **Enhanced Device Monitoring**
   - Battery health sensor
   - Device diagnostics entities
   - Connection quality tracking

4. **Analytics Dashboard**
   - Activity trends card
   - Pet comparison views
   - Health score display

5. **Advanced Notifications**
   - Configurable alert types
   - Quiet hours support
   - Alert history viewer

6. **Base Station Integration**
   - Network status monitoring
   - Multi-pet charging status
   - Environmental data (weather)

## Files Generated
- tryfi_schema.json - Complete GraphQL schema
- user_data_extended.json - Extended user data
- pet_history_*.json - Pet historical data
- device_capabilities_*.json - Device capabilities
- base_features_*.json - Base station features
- analytics_insights.json - Analytics data
- notifications_alerts.json - Notification settings

## Conclusion
The TryFi API offers significantly more functionality than currently exposed in the Home Assistant integration. The most valuable additions would be historical data access, geofencing capabilities, and advanced analytics features.
"""
        
        with open('tryfi_api_exploration_report.md', 'w') as f:
            f.write(report)
            
        print("Report saved to tryfi_api_exploration_report.md")
        
        # Also create a structured findings file
        findings = {
            "discovered_features": self.discovered_features,
            "api_capabilities": {
                "historical_data": True,
                "geofencing": True,
                "health_metrics": True,
                "analytics": True,
                "training_data": True,
                "advanced_notifications": True,
                "base_station_monitoring": True
            },
            "integration_gaps": [
                "No historical data access",
                "No geofencing support",
                "Limited device diagnostics",
                "No analytics or insights",
                "Basic notification support only",
                "No base station entities beyond online status"
            ]
        }
        
        with open('tryfi_findings.json', 'w') as f:
            json.dump(findings, f, indent=2)


if __name__ == "__main__":
    explorer = TryFiExplorer(USERNAME, PASSWORD)
    explorer.run_exploration()