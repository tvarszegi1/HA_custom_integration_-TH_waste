"""Data update coordinator for Érd Waste Collection."""
from datetime import date, timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CITY_URLS, DOMAIN
from .schedule import calculate_schedule, get_feature_street_name

_LOGGER = logging.getLogger(__name__)


class WasteCoordinator(DataUpdateCoordinator[dict[str, list[date]]]):
    """Class to manage fetching Érd waste collection data."""

    def __init__(self, hass: HomeAssistant, config_data: dict) -> None:
        """Initialize the waste coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=12),
        )
        self.city = config_data.get("city", "Érd")
        self.street = config_data.get("street", "")
        self.house_number = str(config_data.get("house_number", "")).strip()
        self.matched_props: dict = {}

        # Master GeoJSON URL for the selected city
        self.url = CITY_URLS.get(self.city)

    async def _async_update_data(self) -> dict[str, list[date]]:
        """Fetch city waste data and compute schedule for configured street."""
        if not self.url:
            raise UpdateFailed(f"No data source URL configured for city '{self.city}'")

        session = async_get_clientsession(self.hass)

        try:
            async with session.get(self.url) as resp:
                resp.raise_for_status()
                geojson_data = await resp.json(content_type=None)
        except Exception as err:
            raise UpdateFailed(f"Error fetching {self.city} waste data from {self.url}: {err}") from err

        features = geojson_data.get("features", [])
        matched_props = None

        # 1. Exact match on normalized street name
        target_street_clean = self.street.strip().lower()
        for feature in features:
            props = feature.get("properties", {})
            f_name = get_feature_street_name(props).lower()
            if f_name == target_street_clean:
                matched_props = props
                break

        # 2. Fallback: if not matched exactly, match prefix (e.g. without house number range in parens)
        if not matched_props:
            for feature in features:
                props = feature.get("properties", {})
                f_name = get_feature_street_name(props).lower()
                base_name = f_name.split("(")[0].strip()
                if base_name and base_name == target_street_clean:
                    matched_props = props
                    break

        if not matched_props:
            _LOGGER.warning(
                "Could not find street '%s' in %s waste database (%d features inspected)",
                self.street,
                self.city,
                len(features),
            )
            return {}

        self.matched_props = matched_props

        # Compute schedule starting from today for the next 180 days
        today = date.today()
        schedule = calculate_schedule(self.city, matched_props, start_date=today, days_ahead=180)
        return schedule