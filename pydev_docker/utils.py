"""
This module provided various utility and helper methods that can be used
generally throughout the package.
"""
from typing import Hashable, Any
import functools
import os


class UtilityError(Exception):
    """
    Generic error of this module
    """


class InvalidDirectory(UtilityError):
    """
    Error occurs when a specified path is not a valid directory
    """


class RegistryKeyError(UtilityError):
    """
    Error occurs when the specified key used to retrieve a value
    from the registry is not registered.
    """


class Registry:
    """
    Object wraps a dictionary to allow various objects to be registered
    into a dictionary, particular useful for functions with the `register_callable`
    decorator.

    Once objects are stored in the registry, they cannot be modified, only retrieved.
    """
    def __init__(self):
        self._registry = {}

    def register(self, key: Hashable, value: Any):
        """
        Registers any key / value combination.

        Args:
            key: The hashable key that identifies the object
            value: The value to store in the registry
        """
        self._registry[key] = value

    def register_callable(self, key: Hashable):
        """
        Decorator, that is invoked withe an identifiable `key` parameter, that
        registers the callable that is decorated.

        Example:
            @registry.register_callable("DELETE")
            def delete_command(options):
                ...

        Args:
            key: The Hashable key to use that identifies the callable in the
                 in the registry.
        """
        def wrapper(f):
            self.register(key, f)

            @functools.wraps(f)
            def wrapped(*args, **kwargs):
                return f(*args, **kwargs)

            return wrapped
        return wrapper

    def get(self, key: Hashable) -> Any:
        """
        Retrieves the value stored in the registry based on the `key` provided.

        Args:
            key: The key used to retrieve the stored object in the registry

        Returns:
            The object stored in the registry based on the `key` parameter

        Raises:
            RegistryKeyError: If the key was not found in the registry
        """
        if key not in self._registry:
            raise RegistryKeyError("Specified key: {} is not in the registry".format(key))

        return self._registry[key]


def get_full_directory_path(path: str) -> str:
    """
    Expands, and validates, any path into an absolute path to a directory.

    Note:
        User constructs "~" or "~user" are expanded

    Args:
        path: The path string of a directory

    Returns:
        An absolute path of a validated directory

    Raises:
        InvalidDirectory: If the specified path was not a valid directory
    """
    full_path = os.path.abspath(os.path.expanduser(path))

    if not full_path:
        raise InvalidDirectory("Invalid path specified: {}".format(path))

    if not os.path.isdir(full_path):
        raise InvalidDirectory("Specified path \"{}\" is not a valid directory".format(path))

    return full_path


def is_python_package_dir(directory: str) -> bool:
    init_path = "{}/__init__.py".format(directory)

    return os.path.isfile(init_path)


def set_default(value, default) -> Any:
    if value is None:
        return default
    return value
