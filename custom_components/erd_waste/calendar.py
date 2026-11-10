"""Calendar platform for Érd Waste Collection."""
from datetime import date, datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, WASTE_TYPE_NAMES
from .coordinator import WasteCoordinator

_LOGGER = logging.getLogger(__name__)

EVENT_EMOJIS = {
    "kommunalis": "🗑️",
    "szelektiv": "♻️",
    "zold": "🌿",
    "uveg": "🍾",
}

EVENT_DESCRIPTIONS = {
    "kommunalis": "Vegyes kommunális hulladékszállítás",
    "szelektiv": "Újrahasznosítható szelektív hulladékszállítás",
    "zold": "Kerti zöldhulladék elszállítás",
    "uveg": "Üveghulladék elszállítás",
}


class WasteCalendarEntity(CoordinatorEntity[WasteCoordinator], CalendarEntity):
    """Representation of the waste collection calendar."""

    def __init__(self, coordinator: WasteCoordinator) -> None:
        """Initialize the waste calendar entity."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.city} Waste Calendar"
        self._attr_unique_id = (
            f"{coordinator.city}_waste_calendar_{coordinator.street}_{coordinator.house_number}"
        )

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
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        today = dt_util.now().date()
        next_events: list[CalendarEvent] = []

        for wtype, dates in self.coordinator.data.items():
            for d in dates:
                if d >= today:
                    emoji = EVENT_EMOJIS.get(wtype, "🗑️")
                    name = WASTE_TYPE_NAMES.get(wtype, wtype.capitalize())
                    next_events.append(
                        CalendarEvent(
                            summary=f"{emoji} {name}",
                            description=EVENT_DESCRIPTIONS.get(wtype, f"{name} szállítás"),
                            start=d,
                            end=d + timedelta(days=1),
                        )
                    )
                    break

        if not next_events:
            return None

        # Sort by start date and return the closest one
        return sorted(next_events, key=lambda e: e.start)[0]

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a specific datetime window for the UI."""
        start_d = start_date.date()
        end_d = end_date.date()
        events: list[CalendarEvent] = []

        for wtype, dates in self.coordinator.data.items():
            emoji = EVENT_EMOJIS.get(wtype, "🗑️")
            name = WASTE_TYPE_NAMES.get(wtype, wtype.capitalize())
            desc = EVENT_DESCRIPTIONS.get(wtype, f"{name} szállítás")

            for d in dates:
                if start_d <= d <= end_d:
                    events.append(
                        CalendarEvent(
                            summary=f"{emoji} {name}",
                            description=desc,
                            start=d,
                            end=d + timedelta(days=1),
                        )
                    )

        return sorted(events, key=lambda e: (e.start, e.summary))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform."""
    coordinator: WasteCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WasteCalendarEntity(coordinator)])