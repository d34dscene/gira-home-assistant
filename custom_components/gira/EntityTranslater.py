import logging
from .entity.EntityType import EntityType
from .entity.GiraLightEntity import GiraLightEntity
from .entity.GiraDimmableLightEntity import GiraDimmableLightEntity
from .entity.GiraOutletEntity import GiraOutletEntity
from .entity.GiraBlindEntity import GiraBlindEntity
from .entity.GiraThermostatEntity import GiraThermostatEntity
from .entity.GiraGarageDoorEntity import GiraGarageDoorEntity


from .PlatformEnumeration import PlatformEnumeration
from .PlatformManager import PlatformManager

import gira_homeserver_api

platformManager = PlatformManager.getInstance()


class EntityTranslator:
    @staticmethod
    def determineEntityType(device):
        searchName = device.getName().lower()
        if searchName.find("leucht") >= 0:
            if isinstance(device, gira_homeserver_api.SwitchableDevice):
                return EntityType.LIGHT, PlatformEnumeration.LIGHT
            elif isinstance(device, gira_homeserver_api.DimmableDevice):
                return EntityType.DIMMABLE_LIGHT, PlatformEnumeration.LIGHT
        elif searchName.find("steckdose") >= 0:
            if isinstance(device, gira_homeserver_api.SwitchableDevice):
                return EntityType.OUTLET, PlatformEnumeration.SWITCH
        elif searchName.endswith("garage\garagentor aufwärts"):
            if isinstance(device, gira_homeserver_api.SequenceDevice):
                return EntityType.GARAGE, PlatformEnumeration.COVER
        elif isinstance(device, gira_homeserver_api.CoverDevice):
            return EntityType.BLIND, PlatformEnumeration.COVER
        elif isinstance(device, gira_homeserver_api.ThermostatDevice):
            return EntityType.THERMOSTAT, PlatformEnumeration.SENSOR

        return EntityType.UNKNOWN, PlatformEnumeration.UNKNOWN
    
    @staticmethod
    def searchForDevice(devices, query):
        query = query.lower()
        for device in devices:
            if device.getName().lower().find(query) >= 0:
                return device

    @staticmethod
    def translate_devices_to_entities(devices):
        entities = {}

        for platform in platformManager.getPlatforms():
            entities[platform] = []

        for device in devices:
            entity = None
            entityType, platform = EntityTranslator.determineEntityType(device)

            if entityType == EntityType.LIGHT:
                entity = GiraLightEntity.create(device)
            elif entityType == EntityType.DIMMABLE_LIGHT:
                entity = GiraDimmableLightEntity.create(device)
            elif entityType == EntityType.OUTLET:
                entity = GiraOutletEntity.create(device)
            elif entityType == EntityType.BLIND:
                entity = GiraBlindEntity.create(device)
            elif entityType == EntityType.THERMOSTAT:
                entity = GiraThermostatEntity.create(device)
            elif entityType == EntityType.GARAGE:
                close_device = EntityTranslator.searchForDevice(devices, "garage\garagentor abwärts")
                entity = GiraGarageDoorEntity.create(device, close_device)

            if (
                platform != PlatformEnumeration.UNKNOWN
                and entityType != EntityType.UNKNOWN
            ):
                entities[platform].append(entity)

        return entities