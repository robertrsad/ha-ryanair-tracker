"""Czujnik ceny Ryanair."""
from datetime import timedelta
import logging
import requests

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    config = config_entry.data
    origin = config["origin"]
    destination = config["destination"]
    date_out = config["date_out"]
    interval = config.get("update_interval_minutes", 60)

    async def async_update_data():
        url = f"https://www.ryanair.com/api/booking/v4/pl-pl/availability?ADT=1&Discount=0&Origin={origin}&Destination={destination}&DateOut={date_out}&RoundTrip=false"
        headers = {"User-Agent": "Mozilla/5.0"}

        def fetch():
            return requests.get(url, headers=headers, timeout=10)

        response = await hass.async_add_executor_job(fetch)
        if response.status_code == 200:
            data = response.json()
            trips = data.get("trips", [])
            if trips and trips[0].get("dates"):
                flights = trips[0]["dates"][0].get("flights", [])
                if flights and "regularFare" in flights[0]:
                    return float(flights[0]["regularFare"]["fares"][0]["amount"])
        return None

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"ryanair_{origin}_{destination}",
        update_method=async_update_data,
        update_interval=timedelta(minutes=interval),
    )

    await coordinator.async_config_entry_first_refresh()
    async_add_entities([RyanairSensor(coordinator, origin, destination, date_out, config_entry.entry_id)])

class RyanairSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, origin, destination, date_out, entry_id):
        super().__init__(coordinator)
        self._origin = origin
        self._destination = destination
        self._date_out = date_out
        self._attr_name = f"Cena Ryanair {origin} ➔ {destination}"
        self._attr_unique_id = f"ryanair_{origin}_{destination}_{date_out}_{entry_id}"
        self._attr_native_unit_of_measurement = "PLN"
        self._attr_icon = "mdi:airplane"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data
