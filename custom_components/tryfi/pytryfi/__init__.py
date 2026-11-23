"""Library dedicated for interacting with tryfi.com"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
import requests

from .fiUser import FiUser
from .fiPet import BehaviorRefresh, FiPet
from .fiBase import FiBase
from .fiDevice import FiDevice
from .fiWifiNetwork import FiWifiNetwork
from .common.query import (
    API_HOST_URL_BASE,
    API_LOGIN,
    getHouseHolds,
    getBaseList,
    getWifiNetworks,
    updateWifiNetwork,
)

__all__ = ["FiDevice", "FiPet", "FiUser", "FiWifiNetwork", "PyTryFi"]

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RefreshStatus:
    """Diagnostic status for one part of the refresh."""

    status: Literal["success", "error", "skipped"]
    last_attempt_at: str | None
    last_success_at: str | None
    error_type: str | None = None


class PyTryFi(object):
    """base object for TryFi"""

    def __init__(self, username=None, password=None):
        self._refresh_status: dict[str, RefreshStatus] = {}
        self._api_host = API_HOST_URL_BASE
        self._session = requests.Session()
        self._user_agent = "pyTryFi"
        self._username = username
        self.login(username, password)

        self._currentUser = FiUser(self._userId)

        userHousehold = getHouseHolds(self._session)
        self._currentUser.setUserDetails(userHousehold)
        self._pets = []
        self._bases = []
        self._householdIds = []
        self._wifiNetworks = []
        for house in userHousehold["userHouseholds"]:
            householdId = house["household"].get("id")
            if householdId:
                self._householdIds.append(householdId)
                LOGGER.debug(f"Found household ID: {householdId}")

            for pet in house["household"]["pets"]:
                # If pet doesn't have a collar then ignore it. What good is a pet without a collar!
                if pet["device"] is None:
                    LOGGER.warning(
                        f"Pet {pet['name']} - {pet['id']} has no collar. Ignoring Pet!"
                    )
                    continue

                p = FiPet(pet["id"])
                p.setCurrentLocation(pet["ongoingActivity"])
                p.setPetDetailsJSON(pet)
                LOGGER.debug(f"Adding Pet: {p._name} with Device: {p._device.deviceId}")
                self._pets.append(p)

            for base in house["household"]["bases"]:
                if base is None:
                    LOGGER.warning("Skipping null base entry in API response")
                    continue
                try:
                    b = FiBase(base["baseId"])
                    b.setBaseDetailsJSON(base)
                    LOGGER.debug(f"Adding Base: {b._name} Online: {b._online}")
                    self._bases.append(b)
                except (KeyError, TypeError, ValueError) as e:
                    LOGGER.warning("Skipping base with invalid data: %s", e)

        # Fetch WiFi networks for each household
        self.updateWifiNetworks()

    def __str__(self):
        instString = f"Username: {self.username}"
        baseString = ""
        petString = ""
        for b in self.bases:
            baseString = baseString + f"{b}"
        for p in self._pets:
            petString = petString + f"{p}"
        return f"TryFi Instance - {instString}\n Pets in Home:\n {petString}\n Bases In Home:\n {baseString}"

    # refresh pet details for all pets
    def updatePets(self) -> None:
        attempted = False
        error_type = None
        try:
            for pet in self._pets:
                behavior: BehaviorRefresh | None = pet.updateAllDetails(self._session)
                if behavior is not None:
                    attempted = True
                    error_type = error_type or behavior.error_type
        finally:
            self._record_refresh("behavior_stats", error_type, attempted=attempted)

    # return the pet object based on petId
    def getPet(self, petId):
        for p in self._pets:
            if petId == p.petId:
                return p
        LOGGER.error(f"Cannot find Pet: {petId}")
        return None

    # refresh base details
    def updateBases(self) -> str | None:
        updatedBases = []
        error_type = None
        baseListJSON = getBaseList(self._session)
        for house in baseListJSON:
            for base in house["household"]["bases"]:
                if base is None:
                    LOGGER.warning("Skipping null base entry in API response")
                    continue
                try:
                    b = FiBase(base["baseId"])
                    b.setBaseDetailsJSON(base)
                    updatedBases.append(b)
                except (KeyError, TypeError, ValueError) as e:
                    LOGGER.warning("Skipping base with invalid data: %s", e)
                    error_type = error_type or type(e).__name__
        self._bases = updatedBases
        return error_type

    # return the pet object based on petId
    def getBase(self, baseId):
        for b in self.bases:
            if baseId == b.baseId:
                return b
        LOGGER.error(f"Cannot find Base: {baseId}")
        return None

    def updateWifiNetworks(self) -> str | None:
        updatedNetworks = []
        error_type = None
        for householdId in self._householdIds:
            try:
                wifiData = getWifiNetworks(self._session, householdId)
                for network in wifiData.get("networks", []):
                    ssid = network.get("ssid")
                    if ssid:
                        w = FiWifiNetwork(ssid, householdId)
                        w.setDetailsJSON(network)
                        LOGGER.debug(f"Adding WiFi Network: {w.ssid} State: {w.state}")
                        updatedNetworks.append(w)
            except Exception as e:
                LOGGER.warning(
                    "failed to fetch WiFi networks for household %s: %s",
                    householdId,
                    e,
                    exc_info=True,
                )
                error_type = error_type or type(e).__name__
        self._wifiNetworks = updatedNetworks
        return error_type

    def getWifiNetwork(self, ssid):
        for w in self._wifiNetworks:
            if w.ssid == ssid:
                return w
        LOGGER.error(f"Cannot find WiFi Network: {ssid}")
        return None

    def setWifiNetworkLocation(self, ssid, latitude, longitude):
        network = self.getWifiNetwork(ssid)
        if not network:
            raise Exception(f"WiFi network not found: {ssid}")
        return updateWifiNetwork(
            self._session, network.householdId, ssid, latitude, longitude
        )

    def update(self):
        for area, label, refresh in (
            ("bases", "base", self.updateBases),
            ("pets", "pets", self.updatePets),
            ("wifi", "wifi networks", self.updateWifiNetworks),
        ):
            try:
                error_type = refresh()
            except Exception as e:
                LOGGER.warning("failed to update %s: %s", label, e, exc_info=True)
                error_type = type(e).__name__
            self._record_refresh(area, error_type)

    def _record_refresh(
        self, area: str, error_type: str | None, *, attempted: bool = True
    ) -> None:
        previous = self._refresh_status.get(area)
        last_attempt_at = previous.last_attempt_at if previous else None
        last_success_at = previous.last_success_at if previous else None
        status: Literal["success", "error", "skipped"] = "skipped"
        if attempted:
            last_attempt_at = datetime.now(UTC).isoformat()
            status = "error" if error_type else "success"
            if error_type is None:
                last_success_at = last_attempt_at
        self._refresh_status[area] = RefreshStatus(
            status, last_attempt_at, last_success_at, error_type
        )

    @property
    def refresh_status(self) -> dict[str, RefreshStatus]:
        """Return a snapshot of per-area refresh outcomes."""
        return self._refresh_status.copy()

    @property
    def currentUser(self):
        return self._currentUser

    @property
    def pets(self) -> list[FiPet]:
        return self._pets

    @property
    def bases(self):
        return self._bases

    @property
    def wifiNetworks(self) -> list[FiWifiNetwork]:
        return self._wifiNetworks

    @property
    def householdIds(self):
        return self._householdIds

    @property
    def username(self):
        return self._username

    @property
    def session(self):
        return self._session

    @property
    def cookies(self):
        return self._cookies

    @property
    def userID(self):
        return self._userId

    # login to the api and get a session
    def login(self, username: str, password: str):
        url = API_HOST_URL_BASE + API_LOGIN
        params = {
            "email": username,
            "password": password,
        }

        LOGGER.debug("Logging into TryFi")
        response = self._session.post(url, data=params)
        response.raise_for_status()
        # validate if the response contains error or not
        json = response.json()
        # if error set or response is non-200
        if "error" in json or not response.ok:
            errorMsg = json["error"].get("message", None)
            LOGGER.error(
                f"Cannot login, response: ({response.status_code}): {errorMsg} "
            )
            raise Exception("TryFiLoginError")

        # storing cookies but don't need them. Handled by session mgmt
        self._cookies = response.cookies
        # store unique userId from login for future use
        self._userId = response.json()["userId"]
        self._sessionId = response.json()["sessionId"]
        LOGGER.debug(f"Successfully logged in. UserId: {self._userId}")

        self.session.headers["content-type"] = "application/json"
