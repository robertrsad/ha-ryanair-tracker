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
        # Używamy oficjalnego API z elastycznym zakresem wokół podanej daty
        url = (
            f"https://www.ryanair.com/api/booking/v4/pl-pl/availability?"
            f"ADT=1&Discount=0&Origin={origin}&Destination={destination}&DateOut={date_out}&RoundTrip=false"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }

        def fetch():
            return requests.get(url, headers=headers, timeout=10)

        try:
            response = await hass.async_add_executor_job(fetch)
            if response.status_code == 200:
                data = response.json()
                trips = data.get("trips", [])
                if trips and "dates" in trips[0]:
                    prices = []
                    for date_entry in trips[0]["dates"]:
                        # Sprawdzamy czy dany dzień zgadza się z naszą datą (lub bierzemy dostępne loty)
                        flights = date_entry.get("flights", [])
                        for flight in flights:
                            if "regularFare" in flight and "fares" in flight["regularFare"]:
                                for fare in flight["regularFare"]["fares"]:
                                    if "amount" in fare:
                                        prices.append(float(fare["amount"]))
                    
                    if prices:
                        # Zwraca najniższą cenę spośród dostępnych lotów tego dnia
                        return min(prices)
            _LOGGER.warning("Nie znaleziono lotów dla %s -> %s na dzień %s (HTTP %s)", origin, destination, date_out, response.status_code)
        except Exception as err:
            _LOGGER.error("Błąd podczas pobierania danych z Ryanair: %s", err)
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
