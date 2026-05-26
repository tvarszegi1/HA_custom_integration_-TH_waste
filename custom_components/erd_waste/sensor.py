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
    """Return a date object for the n-th weekday of a given month."""
    cal = calendar.monthcalendar(year, month)
    dates = [week[weekday_idx] for week in cal if week[weekday_idx] != 0]
    
    if 1 <= n <= len(dates):
        return date(year, month, dates[n-1])
    return None

class WasteSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, waste_type):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._waste_type = waste_type
        
        self._attr_name = f"{coordinator.city} Waste {waste_type.capitalize()}"
        self._attr_unique_id = f"{coordinator.city}_waste_{waste_type}_{coordinator.street}_{coordinator.house_number}"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:trash-can"

    @property
    def native_value(self):
        """Calculate and return the next collection date based on the rule."""
        data = self.coordinator.data.get(self._waste_type)
        if not data:
            return None

        prop_keys = {
            "kommunalis": "kommunalis",
            "szelektiv": "szelektiv",
            "zold": "zoldhulladek",
            "uveg": "uveg" 
        }
        json_key = prop_keys.get(self._waste_type)
        
        target_street = self.coordinator.street
        target_props = {}
        rule = None

        # Grab ALL properties for the street so we can read the hidden 'zoldhulladek2' later
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            feature_street = props.get("name")
            
            if target_street == feature_street:
                target_props = props
                rule = props.get(json_key)
                break

        if not rule:
            return None

        today = date.today()
        current_year = today.year
        current_month = today.month

        try:
            # KOMMUNÁLIS (e.g., "Péntek")
            if self._waste_type == "kommunalis":
                target_weekday = DAYS_HU.get(str(rule).lower())
                if target_weekday is not None:
                    days_ahead = target_weekday - today.weekday()
                    if days_ahead < 0: 
                        days_ahead += 7
                    return today + timedelta(days=days_ahead)

            # SZELEKTÍV (e.g., "1_5_pentek", "3_15_pentek")
            elif self._waste_type == "szelektiv":
                parts = str(rule).lower().split('_')
                
                # Bi-weekly (Kéthetente) logic based on Even/Odd weeks of the year
                if len(parts) >= 2:
                    day_str = parts[-1] 
                    target_weekday = DAYS_HU.get(day_str)
                    
                    if target_weekday is not None:
                        cycle_id = int(parts[0]) if parts[0].isdigit() else 1
                        # Cycles starting with 1 or 3 happen on ODD weeks. Cycles 2 or 4 happen on EVEN weeks.
                        target_is_even = (cycle_id in [2, 4])
                        
                        # Look ahead at the next 4 weeks to find the matching day AND odd/even parity
                        for i in range(28):
                            d = today + timedelta(days=i)
                            if d.weekday() == target_weekday:
                                is_even_week = (d.isocalendar()[1] % 2 == 0)
                                if is_even_week == target_is_even:
                                    return d
                                    
                # Weekly fallback (if a city just specifies a day like "pentek")
                elif len(parts) == 1:
                    target_weekday = DAYS_HU.get(parts[0])
                    if target_weekday is not None:
                        days_ahead = target_weekday - today.weekday()
                        if days_ahead < 0: days_ahead += 7
                        return today + timedelta(days=days_ahead)

            # ZÖLDHULLADÉK (Reads hidden zoldhulladek2 property to find the specific Saturdays)
            elif self._waste_type == "zold":
                target_weekday = 5 # Default to Saturday
                
                z2_val = target_props.get("zoldhulladek2")
                z1_val = target_props.get("zoldhulladek")
                
                target_weeks = []
                # If zoldhulladek2 exists (e.g., 13 or 24), use those exact week numbers!
                if z2_val:
                    target_weeks = [int(x) for x in str(z2_val) if x.isdigit()]
                # Otherwise, try to infer it from the standard zoldhulladek id
                elif z1_val:
                    if int(z1_val) in [1, 3]:
                        target_weeks = [1, 3]
                    elif int(z1_val) in [2, 4]:
                        target_weeks = [2, 4]
                        
                if not target_weeks:
                    target_weeks = [1, 3] # Safe fallback
                
                upcoming_dates = []
                for month_offset in [0, 1]:
                    m = current_month + month_offset
                    y = current_year
                    if m > 12:
                        m = m % 12
                        if m == 0: m = 12
                        if month_offset > 0 and m == 1: y += 1
                        
                    for n in target_weeks:
                        d = get_nth_weekday_of_month(y, m, target_weekday, n)
                        if d and d >= today:
                            upcoming_dates.append(d)
                        
                if upcoming_dates:
                    return min(upcoming_dates)

            # ÜVEG (e.g., "szombat1")
            elif self._waste_type == "uveg":
                rule_str = str(rule).lower()
                
                # Extract the day string (letters only) and week number (digits only)
                day_match = re.search(r'([a-zöüóőúáéí]+)', rule_str)
                week_match = re.search(r'(\d+)', rule_str)
                
                if day_match and week_match:
                    day_str = day_match.group(1)
                    target_week = int(week_match.group(1))
                    target_weekday = DAYS_HU.get(day_str)
                    
                    if target_weekday is not None:
                        upcoming_dates = []
                        for month_offset in [0, 1, 2]: # Look a bit further ahead as glass is usually infrequent
                            m = current_month + month_offset
                            y = current_year
                            if m > 12:
                                m = m % 12
                                if m == 0: m = 12
                                if month_offset > 0 and m == 1: y += 1
                                
                            d = get_nth_weekday_of_month(y, m, target_weekday, target_week)
                            if d and d >= today:
                                upcoming_dates.append(d)
                                
                        if upcoming_dates:
                            return min(upcoming_dates)

        except Exception as e:
            _LOGGER.error(f"Error parsing waste rule '{rule}' for {self._waste_type}: {e}")
            return None

        return None

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for key in coordinator.data.keys():
        entities.append(WasteSensor(coordinator, key))

    async_add_entities(entities)