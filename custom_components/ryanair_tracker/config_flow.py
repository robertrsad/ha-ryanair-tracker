import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

DOMAIN = "ryanair_tracker"

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("origin", default="KRK"): cv.string,
    vol.Required("destination", default="TFS"): cv.string,
    vol.Required("date_out", default="2026-11-10"): cv.string,
    vol.Required("update_interval_minutes", default=60): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
})

class RyanairConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            origin = user_input["origin"].upper().strip()
            destination = user_input["destination"].upper().strip()
            date_out = user_input["date_out"].strip()
            interval = user_input.get("update_interval_minutes", 60)
            
            title = f"{origin} ➔ {destination} ({date_out})"
            
            return self.async_create_entry(
                title=title,
                data={
                    "origin": origin,
                    "destination": destination,
                    "date_out": date_out,
                    "update_interval_minutes": interval
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA
        )
