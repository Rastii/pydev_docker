from typing import Optional, Iterable, Iterator, List
import itertools
import os.path

from pydev_docker import models
from pydev_docker import utils


class ContainerOptions:
    """
    Options for running a docker container
    """
    DEFAULT_PYPATH_DIR = "/pypath"
    DEFAULT_SRC_DIR = "/src"

    def __init__(self,
                 image: str,
                 source_directory: str,
                 *,  # force kwargs only for optional
                 command: Optional[str]=None,
                 container_source_directory: str=DEFAULT_SRC_DIR,
                 environment_variables: Optional[Iterable[models.Environment]]=None,
                 ext_volumes: Optional[Iterable[models.Volume]]=None,
                 network: Optional[str]=None,
                 py_volumes: Optional[Iterable[str]]=None,
                 ports: Optional[Iterable[models.Port]]=None,
                 pypath_directory: str=DEFAULT_PYPATH_DIR,
                 remove_container: bool=True
                 ) -> None:
        """
        Args:
            image: A valid docker image
            source_directory: The absolute path of the development directory that will be
                mounted as the main python "source"
            command: The command that will be ran once the container is created
            pypath_directory: The directory that will contain all of the mounted
                extra python packages, defaults to `ContainerOptions.DEFAULT_PYPATH_DIR`
            container_source_directory: Specifies the directory that will be mounted
                on the docker container that contains the main source code
            py_volumes: The additional python packages
            ext_volumes: Additional volumes to mount that are not related to python packages
            environment_variables: Additional environment variables
            network: The network to connect the container to
            remove_container: Remove the container after the container is finished running
        """

        self._image = image
        self._source_directory = source_directory
        self._command = command
        self._pypath_directory = pypath_directory
        self._container_source_directory = container_source_directory

        self._py_volumes = utils.set_default(py_volumes, [])  # type: Iterable[str]
        self._ext_volumes = utils.set_default(ext_volumes, [])  # type: Iterable[models.Volume]
        self._environment_variables = utils.set_default(
            environment_variables, []
        )  # type: Iterable[models.Environment]
        self._ports = utils.set_default(ports, [])  # type: Iterable[models.Port]

        self._network = network
        self._remove_container = remove_container

    @property
    def image(self) -> str:
        return self._image

    @property
    def command(self) -> Optional[str]:
        return self._command

    @property
    def network(self) -> Optional[str]:
        return self._network

    @property
    def remove_container(self) -> bool:
        return self._remove_container

    def get_source_volume(self) -> models.Volume:
        return models.Volume(
            host_location=self._source_directory,
            container_location=self._container_source_directory,
        )

    def get_pythonpath_environment(self) -> models.Environment:
        return models.Environment("PYTHONPATH", self._pypath_directory)

    def iter_pypath_volumes(self) -> Iterator[models.Volume]:
        for v in self._py_volumes:
            pypath_dir = "{}/{}".format(self._pypath_directory, os.path.basename(v))
            yield models.Volume(v, pypath_dir, mode=models.VolumeMode.RO)

    def iter_ext_volumes(self) -> Iterator[models.Volume]:
        return iter(self._ext_volumes)

    def iter_environment_variables(self) -> Iterator[models.Environment]:
        return iter(self._environment_variables)

    def get_ports(self) -> List[models.Port]:
        return list(self._ports)

    def get_volume_collection(self) -> List[models.Volume]:
        """
        Returns a list of `models.Volume` objects that contains all of the volumes to
        mount, which includes the source volume and all external volumes
        """
        volume_collection = [self.get_source_volume()]
        volume_collection.extend(
            itertools.chain(self.iter_pypath_volumes(), self.iter_ext_volumes())
        )

        return volume_collection

    def get_environment_collection(self) -> List[models.Environment]:
        """
        Returns a list of `models.Environment` objects that contains all of the
        environment variables for the docker container including the PYTHONPATH variable
        """
        environment_collection = [self.get_pythonpath_environment()]
        environment_collection.extend(self.iter_environment_variables())

        return environment_collection
