from enum import Enum
from dataclasses import dataclass

from typing import Dict, List
import xml.etree.ElementTree as ET
import logging

_LOGGER = logging.getLogger(__name__)

class DeviceTypeEnum(Enum):
    LIGHT = "light"
    DIMMER = "dimmer"
    SWITCH = "switch"
    COVER = "cover"
    CLIMATE = "climate"

# INFO: These have to be adjusted depending on the installation
class SlotTypeEnum(Enum):
    LIGHT_SWITCH = "switch"
    DIMMER_SWITCH = "dim_s"
    DIMMER_BRIGHTNESS = "dim_val"
    GENERAL_SWITCH = "slot_switch"
    COVER_SHORT = "slot_short"
    COVER_LONG = "slot_long"
    COVER_POSITION = "slot_position"
    CLIMATE_TARGET = "slot_targetvalue"
    CLIMATE_CURRENT = "slot_temp_actual"

@dataclass
class DeviceConfig:
    name: str
    type: DeviceTypeEnum
    slots: List[SlotTypeEnum]

class Parser:
    def __init__(self, config=None):
        self.devices = {}
        self.config = config or DEFAULT_CONFIG

    def _matches_device_type(self, connections: dict, device_config: DeviceConfig) -> bool:
        """Check if connections match the slots for a device type."""
        connection_slots = set(connections.keys())
        config_slots = {slot.value for slot in device_config.slots}
        return bool(config_slots & connection_slots)

    def _add_device(self, device_id: str, device_name: str, device_config: DeviceConfig, connections: dict) -> None:
        """Create and add a device dictionary with available slots."""
        device_dict = {
            "name": device_name,
            "type": device_config.type.value,
        }

        # Add all matching slots
        for slot in device_config.slots:
            if slot.value in connections:
                device_dict[f"{slot.value}_id"] = connections[slot.value]
                device_dict[f"{slot.value}_val"] = "0.0"

        self.devices[device_id] = device_dict

    def parse(self, xml: str) -> dict:
        """Parse device XML and return devices dict."""
        root = ET.fromstring(xml).find("devices")
        if root is None:
            return self.devices

        # Keep track of device names we've seen
        seen_names = set()

        for device in root.findall("device"):
            device_id = device.attrib.get("id", "0")
            device_name = device.attrib.get("txt", "Unknown Device")

            # Skip devices we've already seen
            if device_name in seen_names:
                continue
            seen_names.add(device_name)

            # Skip devices without any connections
            if len(device.findall("connect")) == 0:
                continue

            # Parse connections
            connections = {
                conn.attrib["slot"]: conn.attrib["tag"]
                for conn in device.findall("connect")
                if "slot" in conn.attrib and "tag" in conn.attrib
            }

            for device_config in self.config.values():
                if self._matches_device_type(connections, device_config):
                    self._add_device(device_id, device_name, device_config, connections)
                    _LOGGER.debug(
                        "Found %s %s, connections: %s",
                        device_config.type.value,
                        device_id,
                        connections
                    )
                    break
            else:
                _LOGGER.debug(
                    "Unknown device type for device %s with connections: %s",
                    device_id,
                    connections
                )

        _LOGGER.debug("Found %s devices", len(self.devices))
        return self.devices

# Default device configurations
DEFAULT_CONFIG: Dict[DeviceTypeEnum, DeviceConfig] = {
    DeviceTypeEnum.LIGHT: DeviceConfig(
        name="",
        type=DeviceTypeEnum.LIGHT,
        slots=[SlotTypeEnum.LIGHT_SWITCH],
    ),
    DeviceTypeEnum.DIMMER: DeviceConfig(
        name="",
        type=DeviceTypeEnum.DIMMER,
        slots=[SlotTypeEnum.DIMMER_SWITCH, SlotTypeEnum.DIMMER_BRIGHTNESS],
    ),
    DeviceTypeEnum.SWITCH: DeviceConfig(
        name="",
        type=DeviceTypeEnum.SWITCH,
        slots=[SlotTypeEnum.GENERAL_SWITCH],
    ),
    DeviceTypeEnum.COVER: DeviceConfig(
        name="",
        type=DeviceTypeEnum.COVER,
        slots=[SlotTypeEnum.COVER_SHORT, SlotTypeEnum.COVER_LONG, SlotTypeEnum.COVER_POSITION],
    ),
    DeviceTypeEnum.CLIMATE: DeviceConfig(
        name="",
        type=DeviceTypeEnum.CLIMATE,
        slots=[SlotTypeEnum.CLIMATE_TARGET, SlotTypeEnum.CLIMATE_CURRENT],
    ),
}
