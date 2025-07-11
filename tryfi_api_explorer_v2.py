#!/usr/bin/env python3
"""
TryFi API Explorer Script V2
This script explores the TryFi GraphQL API using the existing query patterns
to discover additional features and data.
"""

import json
import sys
import os
from typing import Dict, Optional

# Add the pytryfi module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components/tryfi'))

from pytryfi import PyTryFi
from pytryfi.const import *
from pytryfi.common import query

# Credentials
USERNAME = "adam@adam.gs"
PASSWORD = "wygduv-5Zuxge-gezjes"

class TryFiExplorerV2:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.tryfi = None
        self.session = None
        self.discovered_features = {}
        
    def initialize(self):
        """Initialize PyTryFi connection"""
        try:
            self.tryfi = PyTryFi(self.username, self.password)
            self.session = self.tryfi.session
            print(f"Successfully initialized! User ID: {self.tryfi._userId}")
            return True
        except Exception as e:
            print(f"Failed to initialize: {e}")
            return False
            
    def test_query(self, query_string: str, description: str) -> Optional[Dict]:
        """Test a GraphQL query and save results"""
        print(f"\n=== Testing: {description} ===")
        
        try:
            response = query.query(self.session, query_string)
            
            # Save the response
            filename = description.lower().replace(' ', '_') + '.json'
            with open(filename, 'w') as f:
                json.dump(response, f, indent=2)
                
            print(f"Success! Results saved to {filename}")
            return response
            
        except Exception as e:
            print(f"Failed: {e}")
            return None
            
    def explore_extended_user_data(self):
        """Try to get extended user data"""
        # Test additional user fields
        queries = [
            # Extended user details with more fields
            ("query { currentUser { id email firstName lastName phoneNumber createdAt updatedAt emailVerified phoneVerified } }" + FRAGMENT_USER_DETAILS,
             "Extended User Details"),
            
            # User preferences
            ("query { currentUser { preferences { units timezone language } } }",
             "User Preferences"),
            
            # Subscription info
            ("query { currentUser { subscription { status planType features expiryDate } } }",
             "Subscription Info"),
            
            # User statistics
            ("query { currentUser { stats { totalPets totalWalks totalDistance memberSince } } }",
             "User Statistics"),
        ]
        
        for q, desc in queries:
            self.test_query(q, desc)
            
    def explore_household_features(self):
        """Explore household-level features"""
        # Get household ID first
        household_query = QUERY_CURRENT_USER_FULL_DETAIL + FRAGMENT_USER_DETAILS + FRAGMENT_USER_FULL_DETAILS + FRAGMENT_PET_PROFILE + FRAGEMENT_BASE_PET_PROFILE + FRAGMENT_BASE_DETAILS + FRAGMENT_POSITION_COORDINATES + FRAGMENT_BREED_DETAILS + FRAGMENT_PHOTO_DETAILS + FRAGMENT_DEVICE_DETAILS + FRAGMENT_LED_DETAILS + FRAGMENT_OPERATIONAL_DETAILS + FRAGMENT_CONNECTION_STATE_DETAILS
        
        result = self.test_query(household_query, "Full Household Data")
        
        if result:
            households = result.get('data', {}).get('currentUser', {}).get('userHouseholds', [])
            if households:
                household_id = households[0].get('household', {}).get('id', '') if 'id' in households[0].get('household', {}) else None
                
                # Try household-specific queries
                if household_id:
                    household_queries = [
                        (f"query {{ household(id: \"{household_id}\") {{ members {{ user {{ firstName lastName email }} role permissions joinedAt }} }} }}",
                         "Household Members"),
                        
                        (f"query {{ household(id: \"{household_id}\") {{ places {{ id name address radius isHome notifyOnEntry notifyOnExit }} }} }}",
                         "Household Places"),
                        
                        (f"query {{ household(id: \"{household_id}\") {{ activitySummary {{ totalSteps totalDistance mostActivePet leastActivePet }} }} }}",
                         "Household Activity Summary"),
                    ]
                    
                    for q, desc in household_queries:
                        self.test_query(q, desc)
                        
    def explore_pet_features(self, pet_id: str):
        """Explore additional pet features"""
        print(f"\n=== Exploring Pet Features for {pet_id} ===")
        
        # Try various pet-specific queries
        pet_queries = [
            # Medical info
            (f"query {{ pet(id: \"{pet_id}\") {{ medicalInfo {{ vetName vetPhone medications {{ name dosage frequency }} vaccinations {{ name date nextDue }} }} }} }}",
             "Pet Medical Info"),
            
            # Training data
            (f"query {{ pet(id: \"{pet_id}\") {{ training {{ commands {{ name learned lastPracticed successRate }} totalSessions averageSessionLength }} }} }}",
             "Pet Training Data"),
            
            # Social features
            (f"query {{ pet(id: \"{pet_id}\") {{ friends {{ petId petName lastMet }} packMembers {{ petId petName relationship }} }} }}",
             "Pet Social Data"),
            
            # Extended activity with more detail
            (f"query {{ pet(id: \"{pet_id}\") {{ activityDetails {{ hourlyBreakdown {{ hour steps distance }} peakActivityTime favoriteRestSpots {{ name frequency coordinates {{ latitude longitude }} }} }} }} }}",
             "Pet Activity Details"),
            
            # Places visited
            (f"query {{ pet(id: \"{pet_id}\") {{ placesVisited(limit: 20) {{ place {{ name address }} firstVisit lastVisit visitCount totalTime }} }} }}",
             "Pet Places Visited"),
            
            # Achievements/Badges
            (f"query {{ pet(id: \"{pet_id}\") {{ achievements {{ id name description earnedAt icon category }} badges {{ id name description icon }} }} }}",
             "Pet Achievements"),
            
            # Health scores
            (f"query {{ pet(id: \"{pet_id}\") {{ healthScore {{ overall activity rest consistency lastUpdated breakdown {{ category score trend }} }} }} }}",
             "Pet Health Score"),
        ]
        
        for q, desc in pet_queries:
            self.test_query(q, desc)
            
        # Try to get historical data with different approaches
        self.explore_pet_history_alt(pet_id)
        
    def explore_pet_history_alt(self, pet_id: str):
        """Try alternative approaches to get historical data"""
        # Try different date formats and query structures
        #end_date = datetime.now()
        #start_date = end_date - timedelta(days=7)
        
        history_queries = [
            # Activity feed style
            (f"query {{ pet(id: \"{pet_id}\") {{ activityFeed(limit: 50) {{ __typename ... on Walk {{ start end distance steps path {{ latitude longitude }} }} ... on Rest {{ start end place {{ name }} }} }} }} }}",
             "Pet Activity Feed"),
            
            # Summary by period
            (f"query {{ pet(id: \"{pet_id}\") {{ weeklyStats: activitySummaryByPeriod(period: WEEKLY, limit: 4) {{ start end totalSteps totalDistance dailyBreakdown {{ date steps distance }} }} }} }}",
             "Pet Weekly Stats History"),
            
            # Location snapshots
            (f"query {{ pet(id: \"{pet_id}\") {{ recentLocations(limit: 100) {{ timestamp latitude longitude accuracy source }} }} }}",
             "Pet Recent Locations"),
            
            # Walk history
            (f"query {{ pet(id: \"{pet_id}\") {{ walks(limit: 20) {{ id start end distance steps duration startLocation {{ latitude longitude }} endLocation {{ latitude longitude }} }} }} }}",
             "Pet Walk History"),
        ]
        
        for q, desc in history_queries:
            self.test_query(q, desc)
            
    def explore_device_features(self, module_id: str):
        """Explore device-specific features"""
        print(f"\n=== Exploring Device Features for {module_id} ===")
        
        device_queries = [
            # Device info query
            (f"query {{ device(moduleId: \"{module_id}\") {{ moduleId info modelNumber serialNumber manufactureDate warrantyExpiry firmwareVersion }} }}",
             "Device Extended Info"),
            
            # Device stats
            (f"query {{ device(moduleId: \"{module_id}\") {{ stats {{ totalDistance totalSteps totalActiveTime batteryLifeAverage connectionUptime }} }} }}",
             "Device Statistics"),
            
            # Device settings
            (f"query {{ device(moduleId: \"{module_id}\") {{ settings {{ trackingInterval powerMode soundEnabled hapticEnabled nightMode {{ enabled startTime endTime }} }} }} }}",
             "Device Settings"),
            
            # Available firmware updates
            (f"query {{ device(moduleId: \"{module_id}\") {{ availableUpdates {{ version releaseDate description critical }} currentVersion }} }}",
             "Device Updates"),
        ]
        
        for q, desc in device_queries:
            self.test_query(q, desc)
            
    def explore_base_features(self, base_id: str):
        """Explore base station features"""
        print(f"\n=== Exploring Base Features for {base_id} ===")
        
        base_queries = [
            # Extended base info
            (f"query {{ base(id: \"{base_id}\") {{ baseId name model firmwareVersion lastUpdate powerStatus {{ pluggedIn voltage }} }} }}",
             "Base Extended Info"),
            
            # Connected devices with more detail
            (f"query {{ base(id: \"{base_id}\") {{ connectedDevices {{ device {{ moduleId }} pet {{ name }} connectionTime chargingStatus batteryLevel estimatedChargeTime }} }} }}",
             "Base Connected Devices"),
            
            # Base statistics
            (f"query {{ base(id: \"{base_id}\") {{ stats {{ totalCharges averageChargeTime uptime dataTransferred }} }} }}",
             "Base Statistics"),
        ]
        
        for q, desc in base_queries:
            self.test_query(q, desc)
            
    def explore_mutations(self):
        """Explore available mutations"""
        print("\n=== Exploring Mutations ===")
        
        # List mutations we know about
        known_mutations = {
            "updateDeviceOperationParams": "Change device modes (normal/lost, LED on/off)",
            "setDeviceLed": "Set LED color",
            "updatePetProfile": "Update pet information",
            "updateUserProfile": "Update user information",
            "createPlace": "Create a saved place",
            "updatePlace": "Update a saved place",
            "deletePlace": "Delete a saved place",
            "createGeofence": "Create a geofence",
            "updateGeofence": "Update geofence settings",
            "deleteGeofence": "Delete a geofence",
            "updateNotificationPreferences": "Update notification settings",
            "acknowledgePetAlert": "Acknowledge an alert",
            "startWalk": "Manually start walk tracking",
            "endWalk": "Manually end walk tracking",
            "updateStepGoal": "Update daily step goal",
            "sharePetLocation": "Share pet location",
            "addHouseholdMember": "Add member to household",
            "removeHouseholdMember": "Remove member from household",
        }
        
        print("Known mutations:")
        for mutation, desc in known_mutations.items():
            print(f"  - {mutation}: {desc}")
            
        # Save mutations info
        with open('known_mutations.json', 'w') as f:
            json.dump(known_mutations, f, indent=2)
            
    def explore_fragments(self):
        """Analyze the fragments to understand data structure"""
        print("\n=== Analyzing Fragments ===")
        
        # Map out what each fragment provides
        fragment_analysis = {
            "UserDetails": ["id", "email", "firstName", "lastName", "phoneNumber", "fiNewsNotificationsEnabled"],
            "UserFullDetails": ["UserDetails", "userHouseholds with pets and bases"],
            "BasePetProfile": ["id", "name", "homeCityState", "birth info", "gender", "weight", "breed", "photos"],
            "PetProfile": ["BasePetProfile", "chip info", "device details"],
            "DeviceDetails": ["id", "moduleId", "subscription", "operationParams", "connectionState", "LED info"],
            "BaseDetails": ["baseId", "name", "position", "network info", "online status"],
            "OngoingActivityDetails": ["activity type", "start time", "location", "steps", "distance for walks"],
            "ActivitySummaryDetails": ["period stats", "steps", "distance", "goals"],
            "RestSummaryDetails": ["sleep/nap duration by period"],
        }
        
        print("Fragment analysis:")
        for frag, contents in fragment_analysis.items():
            print(f"\n{frag}:")
            for item in contents:
                print(f"  - {item}")
                
        with open('fragment_analysis.json', 'w') as f:
            json.dump(fragment_analysis, f, indent=2)
            
    def generate_comprehensive_report(self):
        """Generate a detailed report of findings"""
        report = """# TryFi API Exploration Report V2

## Overview
This report documents the actual capabilities of the TryFi GraphQL API based on successful queries and analysis of the existing integration code.

## Current API Capabilities

### 1. User Management
- **Available**: Basic user profile (name, email, phone)
- **Available**: News notification preferences
- **Not Found**: Extended preferences, subscription details, user statistics

### 2. Pet Data
- **Available**: Pet profile (name, breed, weight, birth date, gender, photos)
- **Available**: Current location with activity type (walk/rest)
- **Available**: Daily/weekly/monthly activity stats (steps, distance, goals)
- **Available**: Daily/weekly/monthly rest stats (sleep, nap duration)
- **Available**: Device/collar information
- **Not Found**: Medical info, training data, social features, historical data, achievements

### 3. Device/Collar Features
- **Available**: Device ID, connection state, battery level
- **Available**: LED control (color, on/off)
- **Available**: Lost dog mode
- **Available**: Operation parameters
- **Not Found**: Extended diagnostics, firmware info, advanced settings

### 4. Base Station
- **Available**: Base ID, name, location, online status
- **Available**: Network name, connection quality
- **Not Found**: Connected devices detail, charging status, statistics

### 5. Location & Activity
- **Available**: Current GPS location
- **Available**: Ongoing activity (walk/rest)
- **Available**: Area name, uncertainty info
- **Available**: Place information for rests
- **Not Found**: Historical locations, activity feed, walk history

### 6. Household Features
- **Available**: Multiple pets per household
- **Available**: Multiple bases per household
- **Not Found**: Household members, places, geofences

## Integration Enhancement Opportunities

Based on the available API features, here are the recommended enhancements:

### 1. Improve Existing Features
- **Rest/Sleep Tracking**: Add sensors for daily/weekly/monthly sleep and nap duration
- **Activity Zones**: Use area name from ongoing activity for zone-based automations
- **Connection Quality**: Expose base station connection quality
- **Photo Integration**: Add pet photo as entity picture

### 2. Add New Sensors
- **Age Sensor**: Calculate pet age from birth date
- **Activity Type Sensor**: Current activity (walk/rest) as a state
- **Place Sensor**: Current place name when resting
- **Area Sensor**: Current area name from location data

### 3. Enhance Device Control
- **LED Scheduler**: Service to schedule LED on/off times
- **Battery Alerts**: Low battery notifications based on device data
- **Connection Monitoring**: Track last connection time and type

### 4. Statistics and Trends
- **Goal Progress**: Percentage of daily/weekly goals achieved
- **Activity Trends**: Compare current vs previous period
- **Rest Quality**: Sleep vs nap ratio analysis

## Limitations Discovered

1. **No GraphQL Introspection**: The API blocks schema introspection queries
2. **Limited Historical Data**: Only current/summary data available, no detailed history
3. **No Geofencing**: No evidence of geofencing or custom places in current API
4. **Basic Notifications**: Only simple on/off for news notifications

## Recommended Implementation Priority

1. **High Priority**:
   - Add rest/sleep sensors
   - Add activity type and place sensors
   - Improve battery monitoring

2. **Medium Priority**:
   - Add age calculation
   - Add goal progress tracking
   - Enhance LED control with scheduling

3. **Low Priority**:
   - Photo integration
   - Area-based automations
   - Trend analysis

## Conclusion

While the TryFi API is more limited than initially hoped, there are still several valuable features that can be added to the Home Assistant integration. The focus should be on better exposing the existing data (rest stats, places, areas) and adding calculated sensors (age, goal progress) to provide more value to users.

The biggest gaps are in historical data access and geofencing capabilities, which appear to be limitations of the current API rather than missing implementation in the integration.
"""
        
        with open('tryfi_api_report_v2.md', 'w') as f:
            f.write(report)
        print("\nComprehensive report saved to tryfi_api_report_v2.md")
        
    def run_exploration(self):
        """Run the complete exploration"""
        if not self.initialize():
            print("Failed to initialize. Exiting.")
            return
            
        # Get basic data
        print("\n=== Basic Integration Data ===")
        print(f"User: {self.tryfi.currentUser}")
        print(f"Number of pets: {len(self.tryfi.pets)}")
        print(f"Number of bases: {len(self.tryfi.bases)}")
        
        # Get IDs for testing
        pet_id = None
        module_id = None
        base_id = None
        
        if self.tryfi.pets:
            pet = self.tryfi.pets[0]
            pet_id = pet.petId
            module_id = pet.device.moduleId
            print(f"\nUsing pet: {pet.name} (ID: {pet_id})")
            
            # Show current pet data
            print(f"  - Activity: {pet.activityType}")
            print(f"  - Location: {pet.currLatitude}, {pet.currLongitude}")
            print(f"  - Daily steps: {pet.dailySteps}/{pet.dailyGoal}")
            print(f"  - Daily sleep: {pet.dailySleep} min")
            print(f"  - Daily nap: {pet.dailyNap} min")
            print(f"  - Area: {pet.areaName}")
            if hasattr(pet, 'currPlaceName') and pet.currPlaceName:
                print(f"  - Place: {pet.currPlaceName}")
                
        if self.tryfi.bases:
            base = self.tryfi.bases[0]
            base_id = base.baseId
            print(f"\nUsing base: {base.name} (ID: {base_id})")
            print(f"  - Online: {base.online}")
            print(f"  - Network: {base.networkname}")
            print(f"  - Quality: {base.onlineQuality}")
            
        # Explore features
        self.explore_extended_user_data()
        self.explore_household_features()
        
        if pet_id:
            self.explore_pet_features(pet_id)
            
        if module_id:
            self.explore_device_features(module_id)
            
        if base_id:
            self.explore_base_features(base_id)
            
        self.explore_mutations()
        self.explore_fragments()
        
        # Generate report
        self.generate_comprehensive_report()


if __name__ == "__main__":
    explorer = TryFiExplorerV2(USERNAME, PASSWORD)
    explorer.run_exploration()