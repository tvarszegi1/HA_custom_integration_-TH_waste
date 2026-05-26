import calendar
import re
from datetime import date, timedelta
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
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

class WasteSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, waste_type):
        super().__init__(coordinator)
        self._waste_type = waste_type
        self._attr_name = f"{coordinator.city} Waste {waste_type.capitalize()}"
        self._attr_unique_id = f"{coordinator.city}_waste_{waste_type}_{coordinator.street}_{coordinator.house_number}"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:trash-can"

    def _get_upcoming_dates(self):
        """Scans ahead and returns a list of all upcoming collection dates."""
        data = self.coordinator.data.get(self._waste_type)
        if not data: return []

        prop_keys = {"kommunalis": "kommunalis", "szelektiv": "szelektiv", "zold": "zoldhulladek", "uveg": "uveg"}
        json_key = prop_keys.get(self._waste_type)
        
        target_street = self.coordinator.street
        target_props = {}
        rule = None

        for feature in data.get("features", []):
            props = feature.get("properties", {})
            if target_street == props.get("name"):
                target_props = props
                rule = props.get(json_key)
                break

        if not rule: return []

        today = date.today()
        upcoming = []

        try:
            # KOMMUNÁLIS (Next 10 weeks)
            if self._waste_type == "kommunalis":
                target_weekday = DAYS_HU.get(str(rule).lower())
                if target_weekday is not None:
                    days_ahead = target_weekday - today.weekday()
                    if days_ahead < 0: days_ahead += 7
                    for i in range(10):
                        upcoming.append(today + timedelta(days=days_ahead + (7 * i)))

            # SZELEKTÍV (Scan next 150 days)
            elif self._waste_type == "szelektiv":
                parts = str(rule).lower().split('_')
                if len(parts) >= 2:
                    target_weekday = DAYS_HU.get(parts[-1])
                    if target_weekday is not None:
                        cycle_id = int(parts[0]) if parts[0].isdigit() else 1
                        target_is_even = (cycle_id in [2, 4])
                        for i in range(150):
                            d = today + timedelta(days=i)
                            if d.weekday() == target_weekday:
                                if (d.isocalendar()[1] % 2 == 0) == target_is_even:
                                    upcoming.append(d)
                elif len(parts) == 1:
                    target_weekday = DAYS_HU.get(parts[0])
                    if target_weekday is not None:
                        days_ahead = target_weekday - today.weekday()
                        if days_ahead < 0: days_ahead += 7
                        for i in range(10):
                            upcoming.append(today + timedelta(days=days_ahead + (7 * i)))

            # ZÖLDHULLADÉK (Scan next 150 days)
            elif self._waste_type == "zold":
                target_weekday = 5 # Saturday
                z2_val, z1_val = target_props.get("zoldhulladek2"), target_props.get("zoldhulladek")
                target_is_even = True if (str(z2_val) == "13" or str(z1_val) in ["1", "3"]) else False
                
                for i in range(150):
                    d = today + timedelta(days=i)
                    if d.weekday() == target_weekday:
                        if (d.isocalendar()[1] % 2 == 0) == target_is_even:
                            upcoming.append(d)

            # ÜVEG (Scan next 12 months)
            elif self._waste_type == "uveg":
                rule_str = str(rule).lower()
                day_match = re.search(r'([a-zöüóőúáéí]+)', rule_str)
                week_match = re.search(r'(\d+)', rule_str)
                if day_match and week_match:
                    target_weekday = DAYS_HU.get(day_match.group(1))
                    target_week = int(week_match.group(1))
                    if target_weekday is not None:
                        for month_offset in range(12):
                            m = today.month + month_offset
                            y = today.year
                            while m > 12:
                                m -= 12
                                y += 1
                            d = get_nth_weekday_of_month(y, m, target_weekday, target_week)
                            if d and d >= today:
                                upcoming.append(d)

        except Exception as e:
            _LOGGER.error(f"Error parsing waste rule '{rule}': {e}")
            
        return sorted(list(set(upcoming)))

    @property
    def native_value(self):
        """Returns the very next collection date."""
        dates = self._get_upcoming_dates()
        return dates[0] if dates else None

    @property
    def extra_state_attributes(self):
        """Returns a list of the FUTURE collection dates (excluding the current one)."""
        dates = self._get_upcoming_dates()
        if not dates or len(dates) <= 1:
            return {}
            
        # Grab the next 5 dates after the upcoming one
        future_list = [d.strftime("%Y-%m-%d") for d in dates[1:6]]
        return {
            "future_dates": future_list
        }

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WasteSensor(coordinator, key) for key in coordinator.data.keys()])