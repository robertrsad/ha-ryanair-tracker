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
        url = (
            f"https://www.ryanair.com/api/booking/v4/pl-pl/availability?"
            f"ADT=1&Discount=0&Origin={origin}&Destination={destination}&DateOut={date_out}&RoundTrip=false"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pl-PL,pl;q=0.9",
            "client": "desktop",
            "client-version": "3.100.0"
        }

        def fetch():
            return requests.get(url, headers=headers, timeout=12)

        try:
            response = await hass.async_add_executor_job(fetch)
            if response.status_code == 200:
                data = response.json()
                currency = data.get("currency", "PLN")
                trips = data.get("trips", [])
                
                prices = []
                if trips:
                    for trip in trips:
                        for date_entry in trip.get("dates", []):
                            if date_entry.get("dateOut", "").startswith(date_out):
                                for flight in date_entry.get("flights", []):
                                    regular_fare = flight.get("regularFare")
                                    if regular_fare and "fares" in regular_fare:
                                        for fare in regular_fare["fares"]:
                                            if "amount" in fare and fare["amount"] is not None:
                                                prices.append(float(fare["amount"]))

                if prices:
                    min_price = min(prices)
                    return {"price": min_price, "currency": currency}
                else:
                    _LOGGER.warning("Brak lotow bezpośrednich Ryanair dla %s ➔ %s na %s", origin, destination, date_out)
            else:
                _LOGGER.error("Błąd API Ryanair: HTTP %s", response.status_code)
        except Exception as err:
            _LOGGER.error("Błąd połączenia z API Ryanair: %s", err)

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
        self._attr_icon = "mdi:airplane"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if self.coordinator.data and "price" in self.coordinator.data:
            return self.coordinator.data["price"]
        return None

    @property
    def native_unit_of_measurement(self):
        if self.coordinator.data and "currency" in self.coordinator.data:
            return self.coordinator.data["currency"]
        return "PLN"
