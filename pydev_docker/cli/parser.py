from typing import Optional, Sequence, Mapping, List, NamedTuple
import enum
import argparse

import yaml

from pydev_docker import utils
from pydev_docker import options
from pydev_docker import models
from pydev_docker import container


class ParseError(Exception):
    """
    Generic exception related to parsing options
    """


class InvalidOption(ParseError):
    """
    Specified option was invalid
    """


class InvalidVolume(InvalidOption):
    """
    Specified volume was invalid
    """


class Command(enum.IntEnum):
    RUN = 1
    RUN_PTY = 2

    def __str__(self):
        return self.name.lower()


class Verbosity(enum.IntEnum):
    DEBUG = 1
    INFO = 2
    WARN = 3


Arguments = NamedTuple(
    "Arguments",
    [
        ("command", Command),
        ("verbosity", Verbosity),
        ("container_options", options.ContainerOptions),
    ]
)


class YamlParserAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            with open(values) as fp:
                config = yaml.load(fp)
        except (IOError, yaml.YAMLError) as e:
            raise argparse.ArgumentError(self, "Unable to parse YML config: {}".format(e))

        setattr(namespace, self.dest, config)


class DirectoryAction(argparse.Action):
    """
    Action will expand a specified path and ensure that it is a valid directory
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            values = self.default

        try:
            full_path = utils.get_full_directory_path(values)
        except utils.InvalidDirectory:
            raise argparse.ArgumentError(self, "Path '{}' is not a valid directory".format(values))

        setattr(namespace, self.dest, full_path)


def volume_from_str(volume_str: str) -> models.Volume:
    split = volume_str.split(":", 2)

    if len(split) < 2 or len(split) > 3:
        raise InvalidVolume(
            "Specified volume: {} was invalid, must be in the "
            "form of HOST:CONTAINER[:MODE]".format(volume_str)
        )
    if len(split) == 2:
        return models.Volume(
            host_location=split[0],
            container_location=split[1],
        )

    try:
        mode = models.VolumeMode[split[2].upper()]  # type: models.VolumeMode
    except KeyError:
        raise InvalidVolume(
            "Specified mode: {} is invalid, "
            "must be one of {}".format(mode, models.available_volume_modes())
        )

    return models.Volume(
        host_location=split[0],
        container_location=split[1],
        mode=mode,
    )


def environments_from_dict(environment_dict: Mapping) -> List[models.Environment]:
    return [models.Environment(k, v) for k, v in environment_dict.items()]


def _expand_py_paths(path_list: List[str]) -> List[str]:
    expanded_paths = []
    for path in path_list:
        # Attempt to convert the path into a full absolute path
        try:
            full_path = utils.get_full_directory_path(path)
        except utils.InvalidDirectory as e:
            raise InvalidOption(e)

        # Ensure the specified path is a python package
        if not utils.is_python_package_dir(full_path):
            raise InvalidOption(
                "Path: {} is not a valid python package. "
                "Missing expected __init__.py file".format(full_path))

        expanded_paths.append(full_path)

    return expanded_paths


def parse_yml_file(yml_data: Mapping) -> dict:
    # TODO: It would be nice to just re-use the docker-compose parsing methods for this
    parsed_options = {}

    if "python_packages" in yml_data:
        yml_data_py_modules = yml_data["python_packages"]
        # Load any options, if they exist
        if "container_directory" in yml_data_py_modules:
            parsed_options["pypath_directory"] = yml_data_py_modules["container_directory"]

        # Load any paths if they exist
        if "paths" in yml_data_py_modules:
            parsed_options["py_volumes"] = _expand_py_paths(yml_data_py_modules["paths"])

    if "docker_options" in yml_data:
        yml_data_docker_opts = yml_data["docker_options"]
        if "environment" in yml_data_docker_opts:
            parsed_options["environment_variables"] = (
                environments_from_dict(yml_data_docker_opts["environment"])
            )
        if "network" in yml_data_docker_opts:
            parsed_options["network"] = yml_data_docker_opts["network"]
        if "volumes" in yml_data_docker_opts:
            parsed_options["ext_volumes"] = [
                volume_from_str(v) for v in yml_data_docker_opts["volumes"]
            ]

    return parsed_options


def options_from_args_namespace(args: argparse.Namespace) -> options.ContainerOptions:
    kwargs_options = {
        "image": args.image,
        "source_directory": args.directory,
        "command": getattr(args, "command", None),
        "remove_container": not args.keep,
    }

    if args.config:
        kwargs_options.update(parse_yml_file(args.config))

    # The following CLI args overwrite YML config args
    if args.py_packages:
        kwargs_options["py_volumes"] = _expand_py_paths(args.py_packages)

    return options.ContainerOptions(**kwargs_options)


def verbosity_from_int(verbosity_int: int) -> Verbosity:
    return {
        0: Verbosity.WARN,
        1: Verbosity.INFO,
    }.get(verbosity_int, Verbosity.DEBUG)


def add_run_command_args(sub_parser: argparse.ArgumentParser):
    sub_parser.add_argument("image", type=str,
                            help="The docker image to use")

    sub_parser.add_argument("command", type=str,
                            help="The command to run on the container")

    sub_parser.add_argument("directory", nargs="?", type=str, default=".",
                            action=DirectoryAction,
                            help="Specify the directory in which the main python package "
                                 "that is being developed is located in.  Defaults to the "
                                 "current directory")


def add_run_pty_command_args(sub_parser: argparse.ArgumentParser):
    default_pty_cmd = container.PyDevContainer.DEFAULT_PTY_COMMAND
    sub_parser.add_argument("-c", "--command", type=str,
                            default=default_pty_cmd,
                            help="The command to run that spawns a shell, "
                                 "defaults to {}".format(default_pty_cmd))

    sub_parser.add_argument("image", type=str,
                            help="The docker image to use")

    sub_parser.add_argument("directory", nargs="?", type=str, default=".",
                            action=DirectoryAction,
                            help="Specify the directory in which the main python package "
                                 "that is being developed is located in.  Defaults to the "
                                 "current directory")


_EPILOG = """
EXAMPLES
--------

Run a command by mounting the current directory as the source, using the "py3_dev"
docker image, and mounting an additional "NetworkPackage" python package:

    %(prog)s run -p ~/Projects/NetworkPackage py3_dev "python3 setup.py test"

Spawn an interactive shell using the "py3_dev" image on the current directory:

    %(prog)s run_pty py3_dev

CONFIG DOCUMENTATION
--------------------

The following describes the documentation for the configurations expected in the YML file
when using the "-c" or "--config" command:

The **python_packages** section supports the following settings:

    - **container_directory** (*string*): The directory in which the additional python packages
        will be mounted to in the docker container. Defaults to ``/pypath``.
    - **paths** (*list*): A list of paths that are python packages.  Note that this *must* be
        a path of a python package (contains __init__.py).

The **docker_options** section attempts to closely mimic the syntax of docker-compose files.
It contains the following settings:

    - **environment** (*dictionary*): Specifies the environment variables that will be configured
        on the docker container.  Note that ``PYTHONPATH`` will be automatically configured
        and should **not** be used here.
    - **network** (*string*): Specifies a network to connect the container to.  Defaults
        to the default bridge network.
    - **volumes** (*list*): List of ``HOST_LOCATION:CONTAINER_LOCATION[:MODE]`` strings where
        HOST_LOCATION is the location of the volume on the host, CONTAINER_LOCATION is where
        to mount the volume on the container and MODE specifies the mount mode of the volume
        ro (Read-Only) or rw (Read-Write) -- defaults to "rw".
""".strip()


def parse_args(args: Optional[Sequence]=None) -> Arguments:
    """
    Parses arguments from the `args` specified, or `sys.argv` if not specified, and returns
    a `options.ContainerOptions` based on the arguments.

    Args:
        args: Optional list of arguments to parse in the format of command line arguments

    Returns:
        A tuple of the command that was specified and the options
    """
    parser = argparse.ArgumentParser(
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )

    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="When specified, additional logging messages will be displayed to"
                             "STDOUT.  When specified twice, debugging logs will be included")
    parser.add_argument("-c", "--config", type=str,
                        default=None, action=YamlParserAction)
    parser.add_argument("--keep", action="store_true", default=False,
                        help="Keep the container after running a command. "
                             "The default behavior is to remove the container "
                             "after the command has been ran")
    parser.add_argument("-p", "--py-packages", dest="py_packages", action="append",
                        help="Specify directories to mount on the container and append "
                             "the said directory to the $PYTHONPATH environment variable of "
                             "the container")

    subparsers = parser.add_subparsers(dest="docker_command")

    # Parser for the "run" command
    run_parser = subparsers.add_parser(
        str(Command.RUN),
        help="Create a container and run a command",
    )
    add_run_command_args(run_parser)

    # Parser for the "run pty" command
    run_pty_parser = subparsers.add_parser(
        str(Command.RUN_PTY),
        help="Create a container and spawn an interactive shell on the container",
    )
    add_run_pty_command_args(run_pty_parser)

    args_namespace = parser.parse_args(args=args)
    command_type = Command[args_namespace.docker_command.upper()]  # type: Command
    return Arguments(
        command=command_type,
        verbosity=verbosity_from_int(args_namespace.verbose),
        container_options=options_from_args_namespace(args_namespace),
    )
