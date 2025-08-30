from ..const import PET_MODE_NORMAL, PET_MODE_LOST
from ..exceptions import TryFiError, RemoteApiError, ApiNotAuthorizedError
from typing import Literal
import json
import logging
import requests

LOGGER = logging.getLogger(__name__)

API_HOST_URL_BASE   = "https://api.tryfi.com"
API_GRAPHQL         = "/graphql"
API_LOGIN           = "/auth/login"

VAR_PET_ID = "__PET_ID__"

QUERY_CURRENT_USER_FULL_DETAIL  = "query {  currentUser {    ...UserFullDetails  }}"

QUERY_GET_BASES = "query { currentUser { userHouseholds { household { bases { __typename ...BaseDetails }}}}}"
QUERY_PET_ACTIVE_DETAILS = "query {  pet (id: \"" + VAR_PET_ID + "\") { ongoingActivity { __typename ...OngoingActivityDetails } dailyStepStat: currentActivitySummary (period: DAILY) { ...ActivitySummaryDetails } weeklyStepStat: currentActivitySummary (period: WEEKLY) { ...ActivitySummaryDetails } monthlyStepStat: currentActivitySummary (period: MONTHLY) { ...ActivitySummaryDetails } device { __typename moduleId info operationParams {    __typename    ...OperationParamsDetails  }  nextLocationUpdateExpectedBy  lastConnectionState {    __typename    ...ConnectionStateDetails  }  ledColor {    __typename    ...LedColorDetails }} dailySleepStat: restSummaryFeed(cursor: null, period: DAILY, limit: 1) {      __typename      restSummaries {        __typename        ...RestSummaryDetails }} monthlySleepStat: restSummaryFeed(cursor: null, period: MONTHLY, limit: 1) {      __typename      restSummaries {        __typename        ...RestSummaryDetails }} }}"
QUERY_PET_ACTIVITY = "query {  pet (id: \""+VAR_PET_ID+"\") {       dailyStat: currentActivitySummary (period: DAILY) {      ...ActivitySummaryDetails    }    weeklyStat: currentActivitySummary (period: WEEKLY) {      ...ActivitySummaryDetails    }    monthlyStat: currentActivitySummary (period: MONTHLY) {      ...ActivitySummaryDetails    }  }}"
QUERY_PET_CURRENT_LOCATION = "query {  pet (id: \""+VAR_PET_ID+"\") {    ongoingActivity {      __typename      ...OngoingActivityDetails    }  }}"
QUERY_PET_DEVICE_DETAILS = "query {  pet (id: \""+VAR_PET_ID+"\") {    __typename    ...PetProfile  }}"
QUERY_PET_REST = "query {  pet (id: \""+VAR_PET_ID+"\") {	dailyStat: restSummaryFeed(cursor: null, period: DAILY, limit: 1) {      __typename      restSummaries {        __typename        ...RestSummaryDetails      }    }	weeklyStat: restSummaryFeed(cursor: null, period: WEEKLY, limit: 1) {      __typename      restSummaries {        __typename        ...RestSummaryDetails      }    }	monthlyStat: restSummaryFeed(cursor: null, period: MONTHLY, limit: 1) {      __typename      restSummaries {        __typename        ...RestSummaryDetails      }    }  }}"

FRAGMENT_ACTIVITY_SUMMARY_DETAILS = "fragment ActivitySummaryDetails on ActivitySummary {  __typename  totalSteps  stepGoal  totalDistance}"
FRAGMENT_BASE_DETAILS = "fragment BaseDetails on ChargingBase {  __typename  baseId  name  position {    __typename    ...PositionCoordinates  }  infoLastUpdated  networkName  online  onlineQuality}"
FRAGMENT_BASE_PET_PROFILE = "fragment BasePetProfile on BasePet {  __typename  id  name  homeCityState  yearOfBirth  monthOfBirth  dayOfBirth  gender  weight  isPurebred  breed {    __typename    ...BreedDetails  }  photos {    __typename    first {      __typename      ...PhotoDetails    }    items {      __typename      ...PhotoDetails    }  }  }"
FRAGMENT_BREED_DETAILS = "fragment BreedDetails on Breed {  __typename  id  name  }"
FRAGMENT_CONNECTION_STATE_DETAILS = "fragment ConnectionStateDetails on ConnectionState {  __typename  date  ... on ConnectedToUser {    user {      __typename      ...UserDetails    }  }  ... on ConnectedToBase {    chargingBase {      __typename      id    }  }  ... on ConnectedToCellular {    signalStrengthPercent  }  ... on UnknownConnectivity {    unknownConnectivity  }}"
FRAGMENT_DEVICE_DETAILS = "fragment DeviceDetails on Device {  __typename  id  moduleId  info  nextLocationUpdateExpectedBy  operationParams {    __typename    ...OperationParamsDetails  }  lastConnectionState {    __typename    ...ConnectionStateDetails  }  ledColor {    __typename    ...LedColorDetails  }  availableLedColors {    __typename    ...LedColorDetails  }}"
FRAGMENT_LED_DETAILS = "fragment LedColorDetails on LedColor {  __typename  ledColorCode  hexCode  name}"
FRAGMENT_LOCATION_POINT = "fragment LocationPoint on Location {  __typename  date  errorRadius  position {    __typename    ...PositionCoordinates  }}"
FRAGMENT_ONGOING_ACTIVITY_DETAILS = "fragment OngoingActivityDetails on OngoingActivity {  __typename  start  lastReportTimestamp  areaName  ... on OngoingWalk {    distance    positions {      __typename      ...LocationPoint    }    path {      __typename      ...PositionCoordinates    }  }  ... on OngoingRest {    position {      __typename      ...PositionCoordinates    }    place {      __typename      ...PlaceDetails    }  }}"
FRAGMENT_OPERATIONAL_DETAILS = "fragment OperationParamsDetails on OperationParams {  __typename  mode  ledEnabled  ledOffAt}"
FRAGMENT_PET_PROFILE = "fragment PetProfile on Pet {  __typename  ...BasePetProfile  chip {    __typename    shortId  }  device {    __typename    ...DeviceDetails  }}"
FRAGMENT_PHOTO_DETAILS = "fragment PhotoDetails on Photo {  __typename  id  date  image {    __typename    fullSize  }}"
FRAGMENT_PLACE_DETAILS = "fragment PlaceDetails on Place {  __typename  id  name  address  position {    __typename    ...PositionCoordinates  }  radius}"
FRAGMENT_POSITION_COORDINATES = "fragment PositionCoordinates on Position {  __typename  latitude  longitude}"
FRAGMENT_REST_SUMMARY_DETAILS = "fragment RestSummaryDetails on RestSummary {  __typename  start  end  data {    __typename    ... on ConcreteRestSummaryData {      sleepAmounts {        __typename        type        duration      }    }  }}"
FRAGMENT_USER_DETAILS = "fragment UserDetails on User {  __typename   id  email  firstName  lastName  phoneNumber }"
FRAGMENT_USER_FULL_DETAILS = "fragment UserFullDetails on User {  __typename  ...UserDetails  userHouseholds {    __typename    household {      __typename      pets {        __typename        ...PetProfile      }      bases {        __typename        ...BaseDetails      }    }  }}"

MUTATION_DEVICE_OPS = "mutation UpdateDeviceOperationParams($input: UpdateDeviceOperationParamsInput!) {  updateDeviceOperationParams(input: $input) {    __typename    ...DeviceDetails  }}"
MUTATION_SET_LED_COLOR = "mutation SetDeviceLed($moduleId: String!, $ledColorCode: Int!) {  setDeviceLed(moduleId: $moduleId, ledColorCode: $ledColorCode) {    __typename    ...DeviceDetails  }}"


def getHouseHolds(session: requests.Session):
    qString = QUERY_CURRENT_USER_FULL_DETAIL + FRAGMENT_USER_DETAILS \
        + FRAGMENT_USER_FULL_DETAILS + FRAGMENT_PET_PROFILE + FRAGMENT_BASE_PET_PROFILE \
        + FRAGMENT_BASE_DETAILS + FRAGMENT_POSITION_COORDINATES + FRAGMENT_BREED_DETAILS \
        + FRAGMENT_PHOTO_DETAILS + FRAGMENT_DEVICE_DETAILS + FRAGMENT_LED_DETAILS + FRAGMENT_OPERATIONAL_DETAILS \
        + FRAGMENT_CONNECTION_STATE_DETAILS
    response = query(session, qString)
    LOGGER.debug(f"getHouseHolds: {response}")
    return response['data']['currentUser']

# Simplified version of the above, but only gets details about the bases
def getBaseList(session: requests.Session):
    qString = QUERY_GET_BASES + FRAGMENT_BASE_DETAILS + FRAGMENT_POSITION_COORDINATES
    response = query(session, qString)
    LOGGER.debug(f"getBaseList: {response}")
    return response['data']['currentUser']['userHouseholds']

def getCurrentPetLocation(session: requests.Session, petId: str):
    qString = QUERY_PET_CURRENT_LOCATION.replace(VAR_PET_ID, petId) + FRAGMENT_ONGOING_ACTIVITY_DETAILS \
        + FRAGMENT_LOCATION_POINT \
        + FRAGMENT_PLACE_DETAILS + FRAGMENT_POSITION_COORDINATES
    response = query(session, qString)
    LOGGER.debug(f"getCurrentPetLocation: {response}")
    return response['data']['pet']['ongoingActivity']

def getPetAllInfo(session: requests.Session, petId: str):
    qString = QUERY_PET_ACTIVE_DETAILS.replace(VAR_PET_ID, petId) + FRAGMENT_ACTIVITY_SUMMARY_DETAILS + FRAGMENT_ONGOING_ACTIVITY_DETAILS + FRAGMENT_OPERATIONAL_DETAILS + FRAGMENT_CONNECTION_STATE_DETAILS + FRAGMENT_LED_DETAILS \
        + FRAGMENT_REST_SUMMARY_DETAILS + FRAGMENT_POSITION_COORDINATES + FRAGMENT_LOCATION_POINT + FRAGMENT_USER_DETAILS + FRAGMENT_PLACE_DETAILS
    response = query(session, qString)
    LOGGER.debug(f"getPetAllInfo: {response}")
    return response['data']['pet']

def getCurrentPetStats(session: requests.Session, petId: str):
    qString = QUERY_PET_ACTIVITY.replace(VAR_PET_ID, petId) + FRAGMENT_ACTIVITY_SUMMARY_DETAILS
    response = query(session, qString)
    LOGGER.debug(f"getCurrentPetStats: {response}")
    return response['data']['pet']

def getCurrentPetRestStats(session: requests.Session, petId: str):
    qString = QUERY_PET_REST.replace(VAR_PET_ID, petId) + FRAGMENT_REST_SUMMARY_DETAILS
    response = query(session, qString)
    LOGGER.debug(f"getCurrentPetStats: {response}")
    return response['data']['pet']

def getDevicedetails(session: requests.Session, petId: str):
    qString = QUERY_PET_DEVICE_DETAILS.replace(VAR_PET_ID, petId) + FRAGMENT_PET_PROFILE + FRAGMENT_BASE_PET_PROFILE + \
        FRAGMENT_DEVICE_DETAILS + FRAGMENT_LED_DETAILS + FRAGMENT_OPERATIONAL_DETAILS + FRAGMENT_CONNECTION_STATE_DETAILS + \
        FRAGMENT_USER_DETAILS + FRAGMENT_BREED_DETAILS + FRAGMENT_PHOTO_DETAILS
    response = query(session, qString)
    LOGGER.debug(f"getDevicedetails: {response}")
    return response['data']['pet']

def getPetHealthTrends(session: requests.Session, petId: str, period: str = 'DAY'):
    """Get pet health trends including behavior data for Series 3+ collars."""
    # Build the query with the health trends fragment inline
    qString = f"""
    query PetHealthTrends {{
        getPetHealthTrendsForPet(petId: "{petId}", period: {period}) {{
            behaviorTrends {{
                __typename
                id
                title
                summaryComponents {{
                    __typename
                    eventsSummary
                    durationSummary
                }}
            }}
        }}
    }}
    """
    response = query(session, qString)
    LOGGER.debug(f"getPetHealthTrends: {response}")
    return response['data']['getPetHealthTrendsForPet']

def setLedColor(session: requests.Session, deviceId: str, ledColorCode):
    qString = MUTATION_SET_LED_COLOR + FRAGMENT_DEVICE_DETAILS + FRAGMENT_OPERATIONAL_DETAILS + FRAGMENT_CONNECTION_STATE_DETAILS + FRAGMENT_USER_DETAILS + FRAGMENT_LED_DETAILS
    qVariables = '{"moduleId":"'+deviceId+'","ledColorCode":'+str(ledColorCode)+'}'
    response = mutation(session, qString, qVariables)
    LOGGER.debug(f"setLedColor: {response}")
    return response['data']

def turnOnOffLed(session: requests.Session, moduleId, ledEnabled: bool):
    qString = MUTATION_DEVICE_OPS + FRAGMENT_DEVICE_DETAILS + FRAGMENT_OPERATIONAL_DETAILS + FRAGMENT_CONNECTION_STATE_DETAILS + FRAGMENT_USER_DETAILS + FRAGMENT_LED_DETAILS
    qVariables = '{"input": {"moduleId":"'+moduleId+'","ledEnabled":'+str(ledEnabled).lower()+'}}'
    response = mutation(session, qString, qVariables)
    LOGGER.debug(f"turnOnOffLed: {response}")
    return response['data']

def setLostDogMode(session: requests.Session, moduleId, action: bool):
    if action:
        mode = PET_MODE_LOST
    else:
        mode = PET_MODE_NORMAL
    qString = MUTATION_DEVICE_OPS + FRAGMENT_DEVICE_DETAILS + FRAGMENT_OPERATIONAL_DETAILS + FRAGMENT_CONNECTION_STATE_DETAILS + FRAGMENT_USER_DETAILS + FRAGMENT_LED_DETAILS
    qVariables = json.dumps({
        "input": {
            "moduleId": moduleId,
            "mode": mode
        }
    })
    response = mutation(session, qString, qVariables)
    LOGGER.debug(f"setLostDogMode: {response}")
    return response['data']

def getGraphqlURL():
    return API_HOST_URL_BASE + API_GRAPHQL

def mutation(session: requests.Session, qString, qVariables):
    url = getGraphqlURL()
    
    params = {"query": qString, "variables": json.loads(qVariables)}
    return _execute(url, session, params=params, method='POST').json()

def query(session: requests.Session, qString):
    url = getGraphqlURL()
    params = {'query': qString}
    resp = _execute(url, session, params=params)
    if not resp.ok:
        LOGGER.warning(f"non-okay response: (first 10 bytes: {resp.text[:10]})")
    if resp.status_code in [401, 403]:
        raise ApiNotAuthorizedError()
    resp.raise_for_status()
    if not resp.text:
        raise RemoteApiError("Empty response payload from tryfi.com")

    try:
        json_object = resp.json()
    except json.JSONDecodeError as e:
        LOGGER.error(f"Failed to parse JSON response: {resp.text}")
        raise RemoteApiError(f"Invalid JSON response from API: {e}. First few bytes: '{resp.text[:10]}'") from e

    if 'errors' in json_object:
        error_msg = ','.join(map(lambda x: x.get('message', 'Unknown GraphQL error'), json_object['errors']))
        if any(auth_err in error_msg.lower() for auth_err in ['unauthorized', 'unauthenticated', 'authentication', 'forbidden']):
            raise ApiNotAuthorizedError()
        raise RemoteApiError(f"GraphQL error: {error_msg}")

    return json_object

def _execute(url: str, session : requests.Session, method: Literal['GET', 'POST'] = 'GET', params=None) -> requests.Response:
    if method == 'GET':
        return session.get(url, params=params)
    elif method == 'POST':
        return session.post(url, json=params)
    else:
        raise TryFiError(f"Method Passed was invalid: {method}. Only GET and POST are supported")
