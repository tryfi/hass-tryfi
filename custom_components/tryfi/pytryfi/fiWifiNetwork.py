import logging

LOGGER = logging.getLogger(__name__)


class FiWifiNetwork(object):
    def __init__(self, ssid, household_id):
        self._ssid = ssid
        self._householdId = household_id
        self._state = None
        self._addressLabel = None
        self._isHidden = False
        self._latitude = None
        self._longitude = None

    def setDetailsJSON(self, networkJSON):
        self._state = networkJSON.get('state')
        self._addressLabel = networkJSON.get('addressLabel')
        self._isHidden = networkJSON.get('isHidden', False)
        position = networkJSON.get('position')
        if position:
            self._latitude = position.get('latitude')
            self._longitude = position.get('longitude')
        else:
            self._latitude = None
            self._longitude = None

    def __str__(self):
        return (
            f"WiFi Network: {self.ssid} State: {self.state} "
            f"Address: {self.addressLabel} Hidden: {self.isHidden} "
            f"Location: {self.latitude},{self.longitude}"
        )

    @property
    def ssid(self):
        return self._ssid

    @property
    def householdId(self):
        return self._householdId

    @property
    def state(self):
        return self._state

    @property
    def addressLabel(self):
        return self._addressLabel

    @property
    def isHidden(self):
        return self._isHidden

    @property
    def latitude(self):
        return self._latitude

    @property
    def longitude(self):
        return self._longitude
