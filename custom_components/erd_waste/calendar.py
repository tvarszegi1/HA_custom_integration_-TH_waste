import calendar
import re
from datetime import date, datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DAYS_HU = {
    "hétfő": 0, "hetfo": 0,
    "kedd": 1,
    "szerda": 2,
    "csütörtök": 3, "csutortok": 3,
    "péntek": 4, "pentek": 4,
    "szombat": 5,
    "vasárnap": 6, "vasarnap": 6
}

def get_nth_weekday_of_month(year, month, weekday_idx, n):
    cal = calendar.monthcalendar(year, month)
    dates = [week[weekday_idx] for week in cal if week[weekday_idx] != 0]
    if 1 <= n <= len(dates):
        return date(year, month, dates[n-1])
    return None

class WasteCalendarEntity(CoordinatorEntity, CalendarEntity):
    def __init__(self, coordinator):
        """Initialize the calendar entity."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.city} Waste Calendar"
        self._attr_unique_id = f"{coordinator.city}_waste_calendar_{coordinator.street}_{coordinator.house_number}"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event (Required by Home Assistant Core)."""
        # Scan the next 60 days to find the single next upcoming event
        start_time = datetime.now()
        end_time = start_time + timedelta(days=60)
        
        events = self._get_events_in_range(start_time, end_time)
        if events:
            # Sort by date and return the closest one
            return sorted(events, key=lambda e: e.start)[0]
        return None

    async def async_get_events(self, hass, start_date, end_date):
        """Return calendar events within a specific datetime window for the UI."""
        return self._get_events_in_range(start_date, end_date)

    def _get_events_in_range(self, start_date, end_date):
        """Core logic to calculate events between two dates."""
        events = []
        start_d = start_date.date()
        end_d = end_date.date()

        # Gather rules from coordinator data
        rules = {}
        target_props = {}
        prop_keys = {"kommunalis": "kommunalis", "szelektiv": "szelektiv", "zold": "zoldhulladek", "uveg": "uveg"}

        for waste_type, json_key in prop_keys.items():
            data = self.coordinator.data.get(waste_type)
            if not data:
                continue
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                if self.coordinator.street == props.get("name"):
                    target_props[waste_type] = props
                    rules[waste_type] = props.get(json_key)
                    break

        # Scan every single day in the calendar view window
        current_d = start_d
        delta = timedelta(days=1)

        while current_d <= end_d:
            # 1. KOMMUNÁLIS
            if "kommunalis" in rules and rules["kommunalis"]:
                wday = DAYS_HU.get(str(rules["kommunalis"]).lower())
                if current_d.weekday() == wday:
                    events.append(CalendarEvent(
                        summary="🗑️ Kommunális",
                        description="Vegyes kommunális hulladékszállítás",
                        start=current_d,
                        end=current_d + delta,
                    ))

            # 2. SZELEKTÍV
            if "szelektiv" in rules and rules["szelektiv"]:
                parts = str(rules["szelektiv"]).lower().split('_')
                if len(parts) >= 2:
                    wday = DAYS_HU.get(parts[-1])
                    if current_d.weekday() == wday:
                        cycle_id = int(parts[0]) if parts[0].isdigit() else 1
                        target_is_even = (cycle_id in [2, 4])
                        if (current_d.isocalendar()[1] % 2 == 0) == target_is_even:
                            events.append(CalendarEvent(
                                summary="♻️ Szelektív",
                                description="Újrahasznosítható szelektív hulladékszállítás",
                                start=current_d,
                                end=current_d + delta,
                            ))
                elif len(parts) == 1:
                    wday = DAYS_HU.get(parts[0])
                    if current_d.weekday() == wday:
                        events.append(CalendarEvent(
                            summary="♻️ Szelektív",
                            start=current_d,
                            end=current_d + delta,
                        ))

            # 3. ZÖLDHULLADÉK
            if "zold" in rules and rules["zold"]:
                props = target_props.get("zold", {})
                z2_val = props.get("zoldhulladek2")
                z1_val = props.get("zoldhulladek")
                target_is_even = True if (str(z2_val) == "13" or str(z1_val) in ["1", "3"]) else False
                
                if current_d.weekday() == 5:  # Saturday
                    if (current_d.isocalendar()[1] % 2 == 0) == target_is_even:
                        events.append(CalendarEvent(
                            summary="🌿 Zöldhulladék",
                            description="Kerti zöldhulladék elszállítás",
                            start=current_d,
                            end=current_d + delta,
                        ))

            # 4. ÜVEG
            if "uveg" in rules and rules["uveg"]:
                rule_str = str(rules["uveg"]).lower()
                day_match = re.search(r'([a-zöüóőúáéí]+)', rule_str)
                week_match = re.search(r'(\d+)', rule_str)
                if day_match and week_match:
                    wday = DAYS_HU.get(day_match.group(1))
                    target_week = int(week_match.group(1))
                    if current_d.weekday() == wday:
                        if get_nth_weekday_of_month(current_d.year, current_d.month, wday, target_week) == current_d:
                            events.append(CalendarEvent(
                                summary="🍾 Üveg",
                                description="Üveghulladék szállítás",
                                start=current_d,
                                end=current_d + delta,
                            ))

            current_d += delta

        return events


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the calendar platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WasteCalendarEntity(coordinator)])