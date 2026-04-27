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
        rule = None

        for feature in data.get("features", []):
            props = feature.get("properties", {})
            feature_street = props.get("name")
            
            if target_street == feature_street:
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

            # SZELEKTÍV (e.g., "1_6_szombat")
            elif self._waste_type == "szelektiv":
                parts = str(rule).lower().split('_')
                if len(parts) >= 2:
                    day_str = parts[-1] 
                    target_weekday = DAYS_HU.get(day_str)
                    
                    if target_weekday is not None:
                        target_weeks = [int(w) for w in parts[:-1] if w.isdigit()]
                        upcoming_dates = []
                        
                        for month_offset in [0, 1]:
                            m = current_month + month_offset
                            y = current_year
                            if m > 12:
                                m = 1
                                y += 1
                                
                            for n in target_weeks:
                                d = get_nth_weekday_of_month(y, m, target_weekday, n)
                                if d and d >= today:
                                    upcoming_dates.append(d)
                        
                        if upcoming_dates:
                            return min(upcoming_dates)

            # ZÖLDHULLADÉK (e.g., 1)
            elif self._waste_type == "zold":
                # Most zones default to specific weeks (e.g. Zone 1 = 1st and 3rd week, or similar rules)
                # Assuming simple week logic here based on earlier templates. Adjust target_weeks if Diósd's rule differs!
                target_weekday = 5 # Defaulting to Saturday 
                target_weeks = [1, 3] # Adjust based on provider's exact calendar mapping for "1"
                
                upcoming_dates = []
                for month_offset in [0, 1]:
                    m = current_month + month_offset
                    y = current_year
                    if m > 12:
                        m = 1
                        y += 1
                        
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
                                y += 1
                                
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