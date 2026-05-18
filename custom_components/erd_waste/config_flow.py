import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, CONF_CITY, CONF_STREET, CONF_HOUSE_NUMBER, CITIES

class WasteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.city = None
        self.streets = []

    async def async_step_user(self, user_input=None):
        """Step 1: Select the City."""
        if user_input is not None:
            self.city = user_input[CONF_CITY]
            return await self.async_step_street()

        # Create a dropdown of available cities from const.py
        schema = vol.Schema({
            vol.Required(CONF_CITY, default="Érd"): vol.In(list(CITIES.keys())),
        })

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_street(self, user_input=None):
        """Step 2: Select the Street and enter House Number."""
        errors = {}

        if user_input is not None:
            # Combine all data and create the integration entry
            data = {
                CONF_CITY: self.city,
                CONF_STREET: user_input[CONF_STREET],
                CONF_HOUSE_NUMBER: user_input[CONF_HOUSE_NUMBER]
            }
            title = f"{self.city} Waste ({data[CONF_STREET]} {data[CONF_HOUSE_NUMBER]})"
            return self.async_create_entry(title=title, data=data)

        # If we haven't fetched the streets for this city yet, do it now
        if not self.streets:
            session = async_get_clientsession(self.hass)
            # We use the 'kommunalis' file as the master list for streets
            url = CITIES[self.city]["kommunalis"] 
            
            try:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
                    
                    # Extract unique street names, ignoring empty ones
                    street_set = set()
                    for feature in data.get("features", []):
                        props = feature.get("properties", {})
                        street_name = props.get("name")
                        if street_name:
                            street_set.add(street_name)
                            
                    # Sort them alphabetically for the dropdown
                    self.streets = sorted(list(street_set))
            except Exception:
                errors["base"] = "cannot_connect"

        # If fetching failed, show an empty text box as a fallback, otherwise show dropdown
        if self.streets:
            schema = vol.Schema({
                vol.Required(CONF_STREET): vol.In(self.streets),
                vol.Required(CONF_HOUSE_NUMBER): str,
            })
        else:
            schema = vol.Schema({
                vol.Required(CONF_STREET): str,
                vol.Required(CONF_HOUSE_NUMBER): str,
            })

        return self.async_show_form(step_id="street", data_schema=schema, errors=errors)