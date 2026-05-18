![Érd Waste Collection](logo.png)
# HA_custom_integration_-ETH_waste
Custom integration for Home Assistant, which enables collecting  data from ÉTH waste collection shedule.

Installation
1. Open HACS in your HA installation, and add this repository: https://github.com/tvarszegi1/HA_custom_integration_-TH_waste
2. Search for the integration in HACS, then download it.
3. Restart HA as prompted.
4. Navigate to Settings -> Devices & Services in Home Assistant, click "Add Integration". Look for "Érd Waste Collection" -> add.
5. Setup your integration on the UI.

This integration supports the following locations:
1. Érd
2. Diósd
3. Sóskút
4. Tárnok
5. Ráckeresztúr

The integration will create 3 or 4 entities (3 for locations with separate communal / green / selective shedules, and 4 for locations with separate communal / green / selective / glass shedules).
The entities shows the next date for each specific type of waste collection. It will recheck the data in  every 12 hours.
