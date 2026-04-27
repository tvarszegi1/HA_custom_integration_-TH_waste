# HA_custom_integration_-ETH_waste
Custom integration for Home Assistant, which enables collecting  data from ÉTH waste collection shedule.

Installation
1. Find your custom_components folder in your Home Assistant
2. Create a subfolder inside, name it as "erd_waste"
3. Copy all the files from this repository to the erd_waste folder (except the README.md)
4. Navigate to Settings -> Devices & Services in Home Assistant, click "Add Integration". Look for "Érd Waste Collection" -> add.
5. Setup your integration on the UI.

This integration supports the following locations:
1. Érd
2. Diósd
3. Sóskút
4. Tárnok
5. Ráckeresztúr

The integration will create 3 or 4 entities (3 for locations with separate communal / green / selective shedules, and 4 for locations with separate communal / green / selective / glass shedules).
The entities shows the next date for each specific type of waste collection.
