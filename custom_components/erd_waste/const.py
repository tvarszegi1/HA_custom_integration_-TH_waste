"""Constants for Érd Waste Collection integration."""

DOMAIN = "erd_waste"

CONF_CITY = "city"
CONF_STREET = "street"
CONF_HOUSE_NUMBER = "house_number"

# Single primary master GeoJSON URL per city.
# Upstream stores identical feature properties across all waste layer files.
CITY_URLS = {
    "Érd": "https://raw.githubusercontent.com/szabokrissz96/erdzoldhulladek/main/2025/erdkommunalis20253.geojson",
    "Diósd": "https://raw.githubusercontent.com/szabokrissz96/erdzoldhulladek/refs/heads/main/2025/diosdkommunalis2025.geojson",
    "Sóskút": "https://raw.githubusercontent.com/szabokrissz96/erdzoldhulladek/main/soskutkommunalisuj.geojson",
    "Tárnok": "https://raw.githubusercontent.com/szabokrissz96/erdzoldhulladek/refs/heads/main/2025/tarnokkommunalis2025.geojson",
    "Ráckeresztúr": "https://raw.githubusercontent.com/szabokrissz96/erdzoldhulladek/refs/heads/main/2025/rackereszturkommunalis20252.geojson",
}

# Kept for backward compatibility
CITIES = {
    city: {"kommunalis": url} for city, url in CITY_URLS.items()
}

WASTE_TYPE_NAMES = {
    "kommunalis": "Kommunális",
    "szelektiv": "Szelektív",
    "zold": "Zöldhulladék",
    "uveg": "Üveg",
}

WASTE_TYPE_ICONS = {
    "kommunalis": "mdi:trash-can",
    "szelektiv": "mdi:recycle",
    "zold": "mdi:leaf",
    "uveg": "mdi:glass-fragile",
}