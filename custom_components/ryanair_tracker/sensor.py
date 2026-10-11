"""Czujnik ceny Ryanair z użyciem bezproblemowego API Farer."""
from datetime import timedelta
import logging
import requests

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    config = config_entry.data
    origin = config["origin"].upper().strip()
    destination = config["destination"].upper().strip()
    date_out = config["date_out"].strip()
    interval = config.get("update_interval_minutes", 60)

    async def async_update_data():
        # Używamy stabilnego publicznego API wyszukiwania lotów / taryf
        url = f"https://www.ryanair.com/api/farer/v2/oneWayFares?departureAirportIataCode={origin}&arrivalAirportIataCode={destination}&outboundDepartureDateFrom={date_out}&outboundDepartureDateTo={date_out}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

        def fetch():
            return requests.get(url, headers=headers, timeout=15)

        try:
            response = await hass.async_add_executor_job(fetch)
            if response.status_code == 200:
                data = response.json()
                fares = data.get("fares", [])
                
                if fares:
                    # Wyciągamy cenę z pierwszego dopasowanego lotu
                    fare_info = fares[0].get("summary", {}).get("price", {})
                    value = fare_info.get("value")
                    currency = fare_info.get("currencyCode", "PLN")
                    
                    if value is not None:
                        _LOGGER.info("Pobrano cenę Ryanair (%s -> %s %s): %s %s", origin, destination, date_out, value, currency)
                        return {"price": float(value), "currency": currency}
                
                _LOGGER.warning("Brak rozkładowych lotów Ryanair dla %s -> %s na dzień %s", origin, destination, date_out)
            else:
                _LOGGER.error("API Ryanair (farer) zwróciło HTTP status %s", response.status_code)
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
