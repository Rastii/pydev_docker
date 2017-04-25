"""
Module provides validation methods.
"""
import logging

import docker.errors


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """
    Generic module exception that occured during validation
    """


class InvalidImage(ValidationError):
    """
    Invalid image when attempting to start a container
    """


class InvalidNetwork(ValidationError):
    """
    Invalid network when attempting to start a container
    """


def is_valid_image(docker_client: docker.client.DockerClient, image: str) -> bool:
    """
    Returns a boolean that indicates whether the specified `image` exists.

    Args:
        docker_client: An instance of the docker client that will be used to
            query the docker API
        image: The image name or ID string that is being validated

    Returns: Boolean indicating whether or not the `image` is valid
    """
    try:
        docker_client.images.get(image)
    except docker.errors.ImageNotFound:
        return False
    except docker.errors.DockerException as e:
        logger.warning("Error occurred while attempting to retrieve docker image: %s", e)
        return False

    return True


def is_valid_network(docker_client: docker.client.DockerClient, network: str) -> bool:
    """
    Returns a boolean that indicates whether the specified `network` exists.

    Args:
        docker_client: An instance of the docker client that will be used to
            query the docker API
        network: The network name or id string that is being validated.

    Returns: Boolean indicating whether or not the `image` is valid
    """
    try:
        network_list = docker_client.networks.list()
    except docker.errors.NotFound:
        return False
    except docker.errors.DockerException as e:
        logger.warning("Error occurred while attempting to retrieve docker image: %s", e)
        return False

    return any(n.name == network or n.id == network for n in network_list)
