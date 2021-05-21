from enum import Enum


class ConfigurationEnumeration(str, Enum):
    HOST = "host"
    PORT = "port"
    USERNAME = "username"
    PASSWORD = "password"