import aiohttp
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import CITIES

_LOGGER = logging.getLogger(__name__)

class WasteCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_data):
        super().__init__(
            hass,
            _LOGGER,
            name="erd_waste",
            update_interval=timedelta(hours=12),
        )
        self.city = config_data.get("city", "Érd")
        self.street = config_data.get("street", "")
        self.house_number = config_data.get("house_number", "")
        
        # Get the specific URLs for the selected city
        self.urls = CITIES.get(self.city, {})

    async def _async_update_data(self):
        async with aiohttp.ClientSession() as session:
            result = {}
            try:
                for key, url in self.urls.items():
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        result[key] = await resp.json(content_type=None)
            except Exception as e:
                raise UpdateFailed(f"Error fetching {self.city} Waste data: {e}")
            return result