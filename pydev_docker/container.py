from typing import Optional, List, Iterator, Iterable, Dict
import logging
import functools

from pydev_docker import models
from pydev_docker import validate

import docker.client
import docker.errors
import docker.models.containers

import dockerpty


logger = logging.getLogger(__name__)


class ContainerError(Exception):
    """
    Generic module level error where all exceptions in this module
    inherit from
    """


class ContainerPtyError(ContainerError):
    """
    Error occurs when a PTY terminal could not be started from a container
    """


class InvalidImage(ContainerPtyError):
    """
    Invalid image when attempting to start a container
    """


class InvalidNetwork(ContainerPtyError):
    """
    Invalid network when attempting to start a container
    """


def _volume_strings_from_collection(volumes: Optional[Iterable[models.Volume]]) -> List[str]:
    if volumes is None:
        return []

    return [
        "{host}:{container}:{mode}".format(
            host=v.host_location,
            container=v.container_location,
            mode=v.mode.name.lower(),
        ) for v in volumes
    ]


def _environment_from_collection(
        environments: Optional[Iterable[models.Environment]]) -> List[str]:
    if environments is None:
        return []

    return ["{}={}".format(e.name, e.value) for e in environments]


def _port_bindings_from_collection(ports: Optional[Iterable[models.Port]]) -> Dict[int, int]:
    if ports is None:
        return {}

    # Seems backwards here, but this is correct!
    return {p.container_port: p.host_port for p in ports}


def _remove_container(container: docker.models.containers.Container):
    try:
        container.remove()
        logger.info("Successfully removed container %s", container.name)
    except docker.errors.APIError as e:
        logger.error("Error occurred when attempting to remove container: %s", e)
        pass


def _validate_class_options(f):
    """
    Decorator used to help validation some arguments when invoking
    `PyDevContainer` methods.

    In particular, it currently examines the following:
    * image: Ensures that the specified image exists
    * network Ensures that the specified network exists, if specified
    """
    @functools.wraps(f)
    def validation_wrapper(self, *args, **kwargs):
        image = kwargs.pop("image")

        if not image:
            image = args[0]

        if not validate.is_valid_image(self._docker_client, image):
            raise InvalidImage("Specified image {} is not valid".format(image))

        network = kwargs.get("network")
        if network and not validate.is_valid_network(self._docker_client, network):
            raise InvalidNetwork("Specified network {} is not valid".format(network))

        return f(self, image, *args, **kwargs)

    return validation_wrapper


class PyDevContainer:
    """
    Provides methods to run commands on arbitrary docker containers using
    built docker images.
    """
    DEFAULT_PTY_COMMAND = "/bin/bash"

    def __init__(self, docker_client: docker.client.DockerClient) -> None:
        self._docker_client = docker_client

    @_validate_class_options
    def run(self,
            image: str,
            command: str,
            *,  # enforce the rest as kwargs
            environment: Optional[List[models.Environment]]=None,
            network: Optional[str]=None,
            ports: Optional[List[models.Port]]=None,
            remove: bool=True,
            stderr: bool=True,
            volumes: Optional[List[models.Volume]]=None) -> Iterator[bytes]:
        """
        Run a command using a docker container using the specified `image` and
        returns a generator that streams stdout / stderr of the container.

        Args:
            image: The docker container will be built from this image
            command: The command to run on the docker container
            environment: List of environment variables that the container will use
            network: The network that the container will connect to
            ports: List of ports that the container will expose
            remove: Removes container after running the command, defaults to True
            stderr: Returns messages from stderr, defaults to True
            volumes: List of volumes that the container will mount

        Yields:
            A generator that returns the output of the container for each iteration

        Raises:
            ContainerError: If there was an error running the docker container
        """

        try:
            # TODO: Store all running containers so we can kill them gracefully via ctrl-c
            container = self._docker_client.containers.run(
                image=image,
                command=command,
                detach=True,
                environment=_environment_from_collection(environment),
                network_mode=network,
                ports=_port_bindings_from_collection(ports),
                stderr=stderr,
                volumes=_volume_strings_from_collection(volumes),
            )
            logger.info("Successfully created container %s", container.name)
        except docker.errors.DockerException as e:
            raise ContainerError("Unable to run PyDevContainer: {}".format(e)) from e

        try:
            yield from container.logs(stdout=True, stderr=stderr, stream=True)
        except docker.errors.DockerException as e:
            raise ContainerError("Error while running command: {}".format(e)) from e
        finally:
            if remove:
                _remove_container(container)

    @_validate_class_options
    def run_pty(self,
                image: str,
                *,  # enforce the rest as kwargs
                command: str=DEFAULT_PTY_COMMAND,
                environment: Optional[List[models.Environment]]=None,
                network: Optional[str]=None,
                ports: Optional[List[models.Port]]=None,
                remove: bool=True,
                volumes: Optional[List[models.Volume]]=None):
        """
        Runs a docker container and spawns an interactive shell over a pseudo terminal.

        Args:
            image: The docker container will be built from this image
            command: The command to run on the docker container.  This command should spawn
                a shell and defaults to /bin/bash
            environment: List of environment variables that the container will use
            network: The network that the container will connect to
            ports: List of ports that the container will expose
            remove: Removes container after running the command, defaults to True
            volumes: List of volumes that the container will mount
        """
        try:
            container = self._docker_client.containers.create(
                image=image,
                command=command,
                volumes=_volume_strings_from_collection(volumes),
                environment=_environment_from_collection(environment),
                network_mode=network,
                ports=_port_bindings_from_collection(ports),
                tty=True,
                stdin_open=True,
            )
        except docker.errors.DockerException as e:
            raise ContainerError("Unable to create container: {}".format(e)) from e

        # Attempt to start docker pty
        try:
            dockerpty.start(self._docker_client.api, {"Id": container.id})
        except Exception as e:
            raise ContainerPtyError("Unable to start a PTY terminal: {}".format(e)) from e
        finally:
            if remove:
                _remove_container(container)
