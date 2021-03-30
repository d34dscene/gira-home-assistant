def setup_platform(hass, config, add_entities, discovery_info=None):
    translated_devices = hass.data["gira"]["translated_devices"]

    add_entities(translated_devices)