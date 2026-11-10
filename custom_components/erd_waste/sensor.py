"""Sensor platform for Érd Waste Collection."""
from datetime import date
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, WASTE_TYPE_ICONS, WASTE_TYPE_NAMES
from .coordinator import WasteCoordinator

_LOGGER = logging.getLogger(__name__)


class WasteSensor(CoordinatorEntity[WasteCoordinator], SensorEntity):
    """Representation of a waste collection date sensor."""

    def __init__(self, coordinator: WasteCoordinator, waste_type: str) -> None:
        """Initialize the waste sensor."""
        super().__init__(coordinator)
        self._waste_type = waste_type
        type_name = WASTE_TYPE_NAMES.get(waste_type, waste_type.capitalize())
        self._attr_name = f"{coordinator.city} Waste {type_name}"
        self._attr_unique_id = (
            f"{coordinator.city}_waste_{waste_type}_{coordinator.street}_{coordinator.house_number}"
        )
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = WASTE_TYPE_ICONS.get(waste_type, "mdi:trash-can")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information linking all waste entities together."""
        street_label = f"{self.coordinator.street} {self.coordinator.house_number}".strip()
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.city}_{self.coordinator.street}_{self.coordinator.house_number}")},
            name=f"{self.coordinator.city} Waste ({street_label})",
            manufacturer="ÉTH",
            model=f"{self.coordinator.city} Waste Collection",
        )

    @property
    def native_value(self) -> date | None:
        """Return the next collection date."""
        dates = self.coordinator.data.get(self._waste_type, [])
        return dates[0] if dates else None

    @property
    def extra_state_attributes(self) -> dict:
        """Return future collection dates and metadata."""
        dates = self.coordinator.data.get(self._waste_type, [])
        attrs = {
            "waste_type": self._waste_type,
            "waste_name": WASTE_TYPE_NAMES.get(self._waste_type, self._waste_type),
        }
        if len(dates) > 1:
            attrs["future_dates"] = [d.isoformat() for d in dates[1:6]]
        else:
            attrs["future_dates"] = []
        return attrs


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    coordinator: WasteCoordinator = hass.data[DOMAIN][entry.entry_id]

    # If coordinator has data, create sensors for returned types
    # Otherwise fallback to standard types for the city
    waste_types = list(coordinator.data.keys())
    if not waste_types:
        if coordinator.city in ("Diósd", "Tárnok"):
            waste_types = ["kommunalis", "szelektiv", "zold", "uveg"]
        else:
            waste_types = ["kommunalis", "szelektiv", "zold"]

    async_add_entities([WasteSensor(coordinator, wtype) for wtype in waste_types])