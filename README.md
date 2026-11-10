![Érd Waste Collection](logo.png)
# HA_custom_integration_-TH_waste

Custom integration for Home Assistant which provides collection dates and calendars from the ÉTH waste collection schedule.

## Features
- **Accurate Schedule Engine**: Full support for all recycling routes, weekly/bi-weekly/monthly green waste cycles (including winter schedules), communal waste, and glass waste.
- **Sensor Entities**: Separate sensor for each waste type showing the upcoming date and future pickup dates in attributes.
- **Calendar Platform**: Native Home Assistant Calendar support with emoji badges and descriptions.
- **Device Registry Integration**: All sensors and calendar are grouped under a single device card per address.
- **Bilingual**: English and Hungarian localization for setup forms and entity metadata.

## Installation
1. Open HACS in your Home Assistant installation, navigate to **Integrations**, click the 3 dots in the top right, select **Custom repositories**, and add:
   `https://github.com/tvarszegi1/HA_custom_integration_-TH_waste` (Type: Integration)
2. Search for **Érd Waste Collection** in HACS, then download it.
3. Restart Home Assistant as prompted.
4. Navigate to **Settings -> Devices & Services**, click **Add Integration**, search for **Érd Waste Collection**.
5. Select your city and street.

## Supported Locations
1. **Érd** (Kommunális, Szelektív, Zöldhulladék)
2. **Diósd** (Kommunális, Szelektív, Zöldhulladék, Üveg)
3. **Sóskút** (Kommunális, Szelektív, Zöldhulladék)
4. **Tárnok** (Kommunális, Szelektív, Zöldhulladék, Üveg)
5. **Ráckeresztúr** (Kommunális, Szelektív, Zöldhulladék)

The integration checks for schedule updates every 12 hours.

## Dashboard Examples

You can use Markdown cards in Lovelace dashboards, such as:

```yaml
type: markdown
content: |
  ### ♻️ Szelektív (Next 5 Pickups)
  {% for date in state_attr('sensor.erd_waste_szelektiv', 'future_dates') %}
  - {{ date }}
  {% endfor %}

  ### 🌿 Zöldhulladék (Next 5 Pickups)
  {% for date in state_attr('sensor.erd_waste_zold', 'future_dates') %}
  - {{ date }}
  {% endfor %}
```

---
*Disclaimer: This integration is not an official add-on made by ÉTH. The creators are not responsible for the validity of the upstream data.*