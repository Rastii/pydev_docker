from typing import Set
import enum


class ModelError(Exception):
    """
    Generic model error
    """


class VolumeMode(enum.Enum):
    # Read-only mode
    RO = 1
    # Read-write mode
    RW = 2


def available_volume_modes() -> Set[str]:
    return {v.name for v in VolumeMode}  # type: ignore


class Volume:
    """
    Defines a model for a docker volume
    """
    def __init__(self, host_location: str, container_location: str,
                 mode: VolumeMode=VolumeMode.RW) -> None:
        """
        Args:
            host_location: The host location of the volume
            container_location: The container location of the volume
            mode: The mount mode (Read-only / Read-write), optional, defaults to Read-Write.
        """
        self._host_location = host_location
        self._container_location = container_location
        self._mode = mode

    @property
    def host_location(self) -> str:
        return self._host_location

    @property
    def container_location(self) -> str:
        return self._container_location

    @property
    def mode(self) -> VolumeMode:
        return self._mode


class Environment:
    """
    Defines a model for a docker environment variable
    """
    def __init__(self, name: str, value: str) -> None:
        """
        Args:
            name: The environment variable name
            value: The environment variable value
        """
        self._name = name
        self._value = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str:
        return self._value
