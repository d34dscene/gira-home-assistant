import xml.etree.ElementTree as ET
import logging

_LOGGER = logging.getLogger(__name__)

class DeviceType:
    def __init__(self, name: str, slots: list):
        self.name = name
        self.slots = slots

class DeviceParser:
    def __init__(self, device_types=None):
        self.device_types = device_types or DEVICE_TYPES
        self.devices = {}

    @staticmethod
    def _matches_device_type(connections: dict, device_type: DeviceType) -> bool:
        """Check if connections match the slots for a device type."""
        connection_slots = set(connections.keys())
        slots = set(device_type.slots)
        return bool(slots & connection_slots)

    @staticmethod
    def _create_device_dict(device_name: str, device_type: DeviceType, connections: dict) -> dict:
        """Create a device dictionary with all available slots."""
        device_dict = {
            "name": device_name,
            "type": device_type.name,
        }

        # Add all available slots (both required and optional)
        for slot in device_type.slots:
            if slot in connections:
                # Add both ID and value fields
                device_dict[f"{slot}_id"] = connections[slot]
                device_dict[f"{slot}_val"] = "0.0"

        return device_dict

    def parse(self, xml: str) -> dict:
        """Parse device XML and return devices dict."""
        root = ET.fromstring(xml).find("devices")
        if root is None:
            return self.devices

        for device in root.findall("device"):
            device_id = device.attrib.get("id", "0")
            device_name = device.attrib.get("txt", "Unknown Device")

            connections = {
                conn.attrib["slot"]: conn.attrib["tag"]
                for conn in device.findall("connect")
            }

            for device_type in self.device_types.values():
                if self._matches_device_type(connections, device_type):
                    self.devices[device_id] = self._create_device_dict(
                        device_name, device_type, connections
                    )
                    _LOGGER.debug(
                        "Found %s %s, connections: %s",
                        device_type.name,
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


# Default device types (maybe make adjustable in the future)
DEVICE_TYPES = {
    "light": DeviceType(
        name="light",
        slots=["switch", "switch_rm"],
    ),
    "dimmer": DeviceType(
        name="dimmer",
        slots=["dim_s", "dim_val"],
    ),
    "cover": DeviceType(
        name="cover",
        slots=["slot_short", "slot_long", "slot_position"],
    ),
    # "door": DeviceType(
    #     name="door",
    #     slots=["slot_switch"],
    # ),
}
