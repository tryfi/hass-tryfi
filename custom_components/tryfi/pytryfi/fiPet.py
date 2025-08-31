import datetime
import logging
import requests
from .common import query
from .const import PET_ACTIVITY_ONGOINGWALK
from .fiDevice import FiDevice
from .common.response_handlers import parse_fi_date

LOGGER = logging.getLogger(__name__)

class FiPet(object):
    def __init__(self, petId):
        self._petId = petId
        self._name = None
        self._homeCityState = None
        self._yearOfBirth = None
        self._monthOfBirth = None
        self._gender = None
        self._currPlaceName = None
        self._currPlaceAddress = None
        self._device = None
        self._weight = None
        self._lastUpdated = None
        self._locationLastUpdate = None
        self._posAccuracy = None
        
        # Initialize behavior metrics (Series 3+ only)
        self._dailyBarkingCount = 0
        self._dailyBarkingDuration = 0
        self._weeklyBarkingCount = 0
        self._weeklyBarkingDuration = 0
        self._monthlyBarkingCount = 0
        self._monthlyBarkingDuration = 0
        
        self._dailyLickingCount = 0
        self._dailyLickingDuration = 0
        self._weeklyLickingCount = 0
        self._weeklyLickingDuration = 0
        self._monthlyLickingCount = 0
        self._monthlyLickingDuration = 0
        
        self._dailyScratchingCount = 0
        self._dailyScratchingDuration = 0
        self._weeklyScratchingCount = 0
        self._weeklyScratchingDuration = 0
        self._monthlyScratchingCount = 0
        self._monthlyScratchingDuration = 0
        
        self._dailyEatingCount = 0
        self._dailyEatingDuration = 0
        self._weeklyEatingCount = 0
        self._weeklyEatingDuration = 0
        self._monthlyEatingCount = 0
        self._monthlyEatingDuration = 0
        
        self._dailyDrinkingCount = 0
        self._dailyDrinkingDuration = 0
        self._weeklyDrinkingCount = 0
        self._weeklyDrinkingDuration = 0
        self._monthlyDrinkingCount = 0
        self._monthlyDrinkingDuration = 0

    def setPetDetailsJSON(self, petJSON: dict):
        self._name = petJSON.get('name')
        self._homeCityState = petJSON.get('homeCityState')
        self._yearOfBirth = petJSON['yearOfBirth']
        self._monthOfBirth = int(petJSON['monthOfBirth'])
        self._dayOfBirth = int(petJSON['dayOfBirth'])
        self._gender = petJSON.get('gender')
        self._weight = float(petJSON['weight']) if 'weight' in petJSON else None
        self._breed = petJSON['breed'].get('name') if 'breed' in petJSON else None
        try:
            self._photoLink = petJSON['photos']['first']['image']['fullSize']
        except Exception:
            LOGGER.warning("Cannot find photo of your pet. Defaulting to empty string.")
            self._photoLink = ""
        self._device = FiDevice(petJSON['device']['id'])
        self._device.setDeviceDetailsJSON(petJSON['device'])
        self._lastUpdated = datetime.datetime.now()

    def __str__(self):
        return f"Last Updated - {self.lastUpdated} - Pet ID: {self.petId} Name: {self.name} Is Lost: {self.isLost} From: {self.homeCityState} ActivityType: {self.activityType} Located: {self.currLatitude},{self.currLongitude} Last Updated: {self.currStartTime}\n \
            using Device/Collar: {self._device}"
    
    # set the Pet's current location details
    def setCurrentLocation(self, activityJSON):
        activityType = activityJSON['__typename']
        self._activityType = activityType
        self._areaName = activityJSON['areaName']
        self._locationLastUpdate = parse_fi_date(activityJSON['lastReportTimestamp'])
        if activityType == PET_ACTIVITY_ONGOINGWALK:
            currentLocation = activityJSON['positions'][-1]
            self._posAccuracy = currentLocation['errorRadius'] if 'errorRadius' in currentLocation else None
            currentPosition = currentLocation['position']
        else:
            currentPosition = activityJSON['position']

        self._currLongitude = currentPosition['longitude']
        self._currLatitude = currentPosition['latitude']
        self._currStartTime = datetime.datetime.fromisoformat(activityJSON['start'].replace('Z', '+00:00'))

        if 'place' in activityJSON and activityJSON['place'] is not None:
            self._currPlaceName = activityJSON['place']['name']
            self._currPlaceAddress = activityJSON['place']['address']
        else:
            self._currPlaceName = None
            self._currPlaceAddress = None
        self._lastUpdated = datetime.datetime.now()

    # set the Pet's current steps, goals and distance details for daily, weekly and monthly
    def setStats(self, activityJSONDaily, activityJSONWeekly, activityJSONMonthly):
            #distance is in metres
        self._dailyGoal = int(activityJSONDaily['stepGoal'])
        self._dailySteps = int(activityJSONDaily['totalSteps'])
        self._dailyTotalDistance = float(activityJSONDaily['totalDistance'])
        if activityJSONWeekly:
            self._weeklyGoal = int(activityJSONWeekly['stepGoal'])
            self._weeklySteps = int(activityJSONWeekly['totalSteps'])
            self._weeklyTotalDistance = float(activityJSONWeekly['totalDistance'])
        if activityJSONMonthly:
            self._monthlyGoal = int(activityJSONMonthly['stepGoal'])
            self._monthlySteps = int(activityJSONMonthly['totalSteps'])
            self._monthlyTotalDistance = float(activityJSONMonthly['totalDistance'])

        self._lastUpdated = datetime.datetime.now()

    # Update the Stats of the pet
    def updateStats(self, sessionId: requests.Session):
        try:
            pStatsJSON = query.getCurrentPetStats(sessionId,self.petId)
            self.setStats(pStatsJSON['dailyStat'],pStatsJSON['weeklyStat'],pStatsJSON['monthlyStat'])
            return True
        except Exception as e:
            LOGGER.error(f"Could not update stats for Pet {self.name}.\n{e}")
            return False

    def _extractSleep(self, restObject: dict) -> tuple[int | None, int | None]:
        sleep, nap = 0, 0
        sleepData = restObject['restSummaries'][0]['data']
        if 'sleepAmounts' not in sleepData:
            LOGGER.warning(f"Can't extract sleep because sleepAmounts is missing: {restObject}")
            return None, None
        for sleepAmount in sleepData['sleepAmounts']:
            if sleepAmount['type'] == 'SLEEP':
                sleep = int(sleepAmount['duration'])
            if sleepAmount['type'] == "NAP":
                nap = int(sleepAmount['duration'])
        return sleep, nap

    # Update the Stats of the pet
    def updateRestStats(self, sessionId: requests.Session):
        try:
            pRestStatsJSON = query.getCurrentPetRestStats(sessionId,self.petId)
            self._dailySleep, self._dailyNap = self._extractSleep(pRestStatsJSON['dailyStat'])
            self._weeklySleep, self._weeklyNap = self._extractSleep(pRestStatsJSON['weeklyStat'])
            self._monthlySleep, self._monthlyNap = self._extractSleep(pRestStatsJSON['monthlyStat'])
            return True
        except Exception as e:
            LOGGER.error(f"Could not update rest stats for Pet {self.name}\n{pRestStatsJSON}.\n{e}", exc_info=True)
            return False

    # Update the Pet's GPS location
    def updatePetLocation(self, sessionId: requests.Session):
        try:
            pLocJSON = query.getCurrentPetLocation(sessionId,self.petId)
            self.setCurrentLocation(pLocJSON)
            return True
        except Exception as e:
            LOGGER.error(f"Could not update Pet: {self.name}'s location.\n{e}")
            return False
    
    # Update the device/collar details for this pet
    def updateDeviceDetails(self, sessionId: requests.Session):
        try:
            deviceJSON = query.getDevicedetails(sessionId, self.petId)
            self.device.setDeviceDetailsJSON(deviceJSON['device'])
            return True
        except Exception as e:
            LOGGER.error(f"Could not update Device/Collar information for Pet: {self.name}\n{e}")
            return False

    # Update all details regarding this pet
    def updateAllDetails(self, sessionId: requests.Session):
        petJson = query.getPetAllInfo(sessionId, self.petId)
        self.device.setDeviceDetailsJSON(petJson['device'])
        self.setCurrentLocation(petJson['ongoingActivity'])
        self.setStats(petJson['dailyStepStat'], petJson['weeklyStepStat'], petJson['monthlyStepStat'])
        # TODO: Support weekly
        self._dailySleep, self._dailyNap = self._extractSleep(petJson['dailySleepStat'])
        self._monthlySleep, self._monthlyNap = self._extractSleep(petJson['monthlySleepStat'])

        if self.device.supportsAdvancedBehaviorStats():
            # Try to fetch behavior data for Series 3+ collars
            try:
                self.updateBehaviorStats(sessionId)
            except Exception as e:
                LOGGER.debug(f"Could not update behavior stats for Pet {self.name}. This may be an older collar model.\n{e}")
                # Behavior stats may not be available for older collars
                pass

    # Update behavior stats for Series 3+ collars
    def updateBehaviorStats(self, sessionId: requests.Session):
        """Update behavior statistics for Series 3+ collars."""
        healthTrendsJSON = query.getPetHealthTrends(sessionId, self.petId, 'DAY')
        behavior_trends = healthTrendsJSON.get('behaviorTrends', [])
        self.setBehaviorStatsFromTrends(behavior_trends)

    def setBehaviorStatsFromTrends(self, behaviorTrends):
        """Parse behavior data from health trends API."""
        # Reset all metrics
        self._dailyBarkingCount = 0
        self._dailyBarkingDuration = 0
        self._dailyLickingCount = 0
        self._dailyLickingDuration = 0
        self._dailyScratchingCount = 0
        self._dailyScratchingDuration = 0
        self._dailyEatingCount = 0
        self._dailyEatingDuration = 0
        self._dailyDrinkingCount = 0
        self._dailyDrinkingDuration = 0

        for trend in behaviorTrends:
            if not isinstance(trend, dict):
                LOGGER.warning(f"Found non-dict item ('{type(trend)}') in behaviorTrends. Skipping.")
                continue

            trend_id = trend.get('id', '')
            summary = trend.get('summaryComponents', {})

            # Extract events count
            events_summary = summary.get('eventsSummary')
            events_count = 0
            if events_summary is None:
                # This will be None when the collar doesn't support the stat
                # Skip it and move to the next one
                continue
            if events_summary and 'event' in events_summary:
                events_count = int(events_summary.split()[0])

            # Extract duration
            duration_summary = summary.get('durationSummary')
            duration_seconds = 0
            if duration_summary:
                if duration_summary.startswith('<'):
                    duration_seconds = 30
                else:
                    parts = duration_summary.replace('h', '').replace('m', '').split()
                    if len(parts) == 2:
                        duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60
                    elif 'h' in duration_summary:
                        duration_seconds = int(parts[0]) * 3600
                    else:
                        duration_seconds = int(parts[0]) * 60

            # Map to our attributes
            if trend_id == 'barking:DAY':
                self._dailyBarkingCount = events_count
                self._dailyBarkingDuration = duration_seconds
            elif trend_id == 'cleaning_self:DAY':
                self._dailyLickingCount = events_count
                self._dailyLickingDuration = duration_seconds
            elif trend_id == 'scratching:DAY':
                self._dailyScratchingCount = events_count
                self._dailyScratchingDuration = duration_seconds
            elif trend_id == 'eating:DAY':
                self._dailyEatingCount = events_count
                self._dailyEatingDuration = duration_seconds
            elif trend_id == 'drinking:DAY':
                self._dailyDrinkingCount = events_count
                self._dailyDrinkingDuration = duration_seconds

    # set the color code of the led light on the pet collar
    def setLedColorCode(self, sessionId: requests.Session, colorCode):
        try:
            moduleId = self.device.moduleId
            ledColorCode = int(colorCode)
            setColorJSON = query.setLedColor(sessionId, moduleId, ledColorCode)
            try:
                self.device.setDeviceDetailsJSON(setColorJSON['setDeviceLed'])
            except Exception as e:
                LOGGER.warning(f"Updated LED Color but could not get current status for Pet: {self.name}\nException: {e}")
            return True
        except Exception as e:
            LOGGER.error(f"Could not complete Led Color request:\n{e}")
            return False
    
    # turn on or off the led light. action = True will enable the light, false turns off the light
    def turnOnOffLed(self, sessionId, action):
        try:
            moduleId = self.device.moduleId
            onOffResponse = query.turnOnOffLed(sessionId, moduleId, action)
            try:
                self.device.setDeviceDetailsJSON(onOffResponse['updateDeviceOperationParams'])
            except Exception:
                LOGGER.warning(f"Action: {action} was successful however unable to get current status for Pet: {self.name}")
            return True
        except Exception as e:
            LOGGER.error(f"Could not complete LED request:\n{e}")
            return False

    # set the lost dog mode to Normal or Lost Dog. Action is true for lost dog and false for normal (not lost)
    def setLostDogMode(self, sessionId, action):
        try:
            moduleId = self.device.moduleId
            petModeResponse = query.setLostDogMode(sessionId, moduleId, action)
            try:
                self.device.setDeviceDetailsJSON(petModeResponse['updateDeviceOperationParams'])
            except Exception:
                LOGGER.warning(f"Action: {action} was successful however unable to get current status for Pet: {self.name}")
            return True
        except Exception as e:
            LOGGER.error(f"Could not complete turn on/off light where ledEnable is {action}.\nException: {e}")
            return False

    @property
    def device(self):
        return self._device
    @property
    def petId(self):
        return self._petId
    @property
    def name(self):
        return self._name
    @property
    def homeCityState(self):
        return self._homeCityState
    @property
    def yearOfBirth(self):
        return self._yearOfBirth
    @property
    def monthOfBirth(self):
        return self._monthOfBirth
    @property
    def dayOfBirth(self):
        return self._dayOfBirth
    @property
    def gender(self):
        return self._gender
    @property
    def weight(self):
        return self._weight
    @property
    def breed(self):
        return self._breed
    @property
    def photoLink(self) -> str | None:
        return self._photoLink
    @property
    def currLongitude(self) -> float | None:
        return self._currLongitude
    @property
    def currLatitude(self) -> float | None:
        return self._currLatitude
    @property
    def positionAccuracy(self) -> float | None:
        return self._posAccuracy
    @property
    def currStartTime(self):
        return self._currStartTime
    @property
    def currPlaceName(self):
        return self._currPlaceName
    @property
    def currPlaceAddress(self):
        return self._currPlaceAddress
    @property
    def dailyGoal(self):
        return self._dailyGoal
    @property
    def dailySteps(self):
        return self._dailySteps
    @property
    def dailyTotalDistance(self):
        return self._dailyTotalDistance
    @property
    def weeklyGoal(self):
        return self._weeklyGoal
    @property
    def weeklySteps(self):
        return self._weeklySteps
    @property
    def weeklyTotalDistance(self):
        return self._weeklyTotalDistance
    @property
    def monthlyGoal(self):
        return self._monthlyGoal
    @property
    def monthlySteps(self):
        return self._monthlySteps
    @property
    def monthlyTotalDistance(self):
        return self._monthlyTotalDistance

    @property
    def dailySleep(self):
        return self._dailySleep
    @property
    def weeklySleep(self):
        return self._weeklySleep
    @property
    def monthlySleep(self):
        return self._monthlySleep
    @property
    def dailyNap(self):
        return self._dailyNap
    @property
    def weeklyNap(self):
        return self._weeklyNap
    @property
    def monthlyNap(self):
        return self._monthlyNap
    
    @property
    def locationLastUpdate(self):
        return self._locationLastUpdate
    @property
    def locationNextEstimatedUpdate(self):
        return self._device._nextLocationUpdatedExpectedBy

    @property
    def lastUpdated(self):
        return self._lastUpdated
    @property
    def isLost(self):
        return self.device.isLost
    @property
    def activityType(self):
        return self._activityType
    @property
    def areaName(self):
        return self._areaName
    
    @property
    def signalStrength(self):
        return self._connectionSignalStrength

    def getCurrPlaceName(self):
        return self.currPlaceName
    
    def getCurrPlaceAddress(self):
        return self.currPlaceAddress

    def getActivityType(self):
        return self.activityType

    def getBirthDate(self):
        return datetime.datetime(self.yearOfBirth, self.monthOfBirth, self.dayOfBirth)
    
    def getDailySteps(self):
        return self.dailySteps
    
    def getDailyGoal(self):
        return self.dailyGoal

    def getDailyDistance(self):
        return self.dailyTotalDistance

    def getWeeklySteps(self):
        return self.weeklySteps
    
    def getWeeklyGoal(self):
        return self.weeklyGoal

    def getWeeklyDistance(self):
        return self.weeklyTotalDistance

    def getMonthlySteps(self):
        return self.monthlySteps
    
    def getMonthlyGoal(self):
        return self.monthlyGoal

    def getMonthlyDistance(self):
        return self.monthlyTotalDistance
    
    # Behavior properties (Series 3+ only)
    @property
    def dailyBarkingCount(self):
        return self._dailyBarkingCount
    @property
    def dailyBarkingDuration(self):
        return self._dailyBarkingDuration
    @property
    def weeklyBarkingCount(self):
        return self._weeklyBarkingCount
    @property
    def weeklyBarkingDuration(self):
        return self._weeklyBarkingDuration
    @property
    def monthlyBarkingCount(self):
        return self._monthlyBarkingCount
    @property
    def monthlyBarkingDuration(self):
        return self._monthlyBarkingDuration
    
    @property
    def dailyLickingCount(self):
        return self._dailyLickingCount
    @property
    def dailyLickingDuration(self):
        return self._dailyLickingDuration
    @property
    def weeklyLickingCount(self):
        return self._weeklyLickingCount
    @property
    def weeklyLickingDuration(self):
        return self._weeklyLickingDuration
    @property
    def monthlyLickingCount(self):
        return self._monthlyLickingCount
    @property
    def monthlyLickingDuration(self):
        return self._monthlyLickingDuration
    
    @property
    def dailyScratchingCount(self):
        return self._dailyScratchingCount
    @property
    def dailyScratchingDuration(self):
        return self._dailyScratchingDuration
    @property
    def weeklyScratchingCount(self):
        return self._weeklyScratchingCount
    @property
    def weeklyScratchingDuration(self):
        return self._weeklyScratchingDuration
    @property
    def monthlyScratchingCount(self):
        return self._monthlyScratchingCount
    @property
    def monthlyScratchingDuration(self):
        return self._monthlyScratchingDuration
    
    @property
    def dailyEatingCount(self):
        return self._dailyEatingCount
    @property
    def dailyEatingDuration(self):
        return self._dailyEatingDuration
    @property
    def weeklyEatingCount(self):
        return self._weeklyEatingCount
    @property
    def weeklyEatingDuration(self):
        return self._weeklyEatingDuration
    @property
    def monthlyEatingCount(self):
        return self._monthlyEatingCount
    @property
    def monthlyEatingDuration(self):
        return self._monthlyEatingDuration
    
    @property
    def dailyDrinkingCount(self):
        return self._dailyDrinkingCount
    @property
    def dailyDrinkingDuration(self):
        return self._dailyDrinkingDuration
    @property
    def weeklyDrinkingCount(self):
        return self._weeklyDrinkingCount
    @property
    def weeklyDrinkingDuration(self):
        return self._weeklyDrinkingDuration
    @property
    def monthlyDrinkingCount(self):
        return self._monthlyDrinkingCount
    @property
    def monthlyDrinkingDuration(self):
        return self._monthlyDrinkingDuration
        
