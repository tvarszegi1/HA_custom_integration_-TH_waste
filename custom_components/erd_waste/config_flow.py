"""Config flow for Érd Waste Collection integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CITY_URLS,
    CONF_CITY,
    CONF_HOUSE_NUMBER,
    CONF_STREET,
    DOMAIN,
)
from .schedule import get_feature_street_name

_LOGGER = logging.getLogger(__name__)


class WasteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Érd Waste Collection."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.city: str = "Érd"
        self.streets: list[str] = []

    async def async_step_user(self, user_input=None):
        """Step 1: Select the City."""
        if user_input is not None:
            self.city = user_input[CONF_CITY]
            return await self.async_step_street()

        # Dropdown of available cities
        schema = vol.Schema({
            vol.Required(CONF_CITY, default=self.city): vol.In(list(CITY_URLS.keys())),
        })

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_street(self, user_input=None):
        """Step 2: Select the Street and enter House Number."""
        errors = {}

        if user_input is not None:
            street = user_input[CONF_STREET]
            house_num = str(user_input.get(CONF_HOUSE_NUMBER, "")).strip()

            # Set title for the integration entry
            title_suffix = f"{street} {house_num}".strip()
            title = f"{self.city} Waste ({title_suffix})"

            # Prevent duplicate entries for the same city, street, and house number
            unique_id = f"{self.city}_{street}_{house_num}".lower()
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            data = {
                CONF_CITY: self.city,
                CONF_STREET: street,
                CONF_HOUSE_NUMBER: house_num,
            }
            return self.async_create_entry(title=title, data=data)

        # Fetch streets for the selected city if not yet cached
        if not self.streets:
            session = async_get_clientsession(self.hass)
            url = CITY_URLS.get(self.city)

            if url:
                try:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        data = await resp.json(content_type=None)

                        street_set = set()
                        for feature in data.get("features", []):
                            props = feature.get("properties", {})
                            street_name = get_feature_street_name(props)
                            if street_name:
                                street_set.add(street_name)

                        self.streets = sorted(list(street_set))
                except Exception as err:
                    _LOGGER.error("Failed to fetch street list for %s: %s", self.city, err)
                    errors["base"] = "cannot_connect"

        # Show dropdown if streets were retrieved, otherwise fallback to text input
        if self.streets:
            schema = vol.Schema({
                vol.Required(CONF_STREET): vol.In(self.streets),
                vol.Optional(CONF_HOUSE_NUMBER, default=""): str,
            })
        else:
            schema = vol.Schema({
                vol.Required(CONF_STREET): str,
                vol.Optional(CONF_HOUSE_NUMBER, default=""): str,
            })

        return self.async_show_form(step_id="street", data_schema=schema, errors=errors)