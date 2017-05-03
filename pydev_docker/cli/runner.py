"""
Module provides an entry point to run pydev_docker in the CLI.

This module can be ran directly or invoked through the `setup.py`
entry_points when built.
"""
import sys
import logging

import docker
import docker.errors

from pydev_docker import cli
import pydev_docker.cli.parser

from pydev_docker import container
from pydev_docker import utils
import pydev_docker.options


class Error(Exception):
    """
    Generic error for the module
    """


class DispatcherError(Error):
    """
    An error occurred while attempting to dispatch a command
    """


class CommandDispatcher:
    """
    Provides a dispatcher to invoke methods on `container.PyDevContainer`
    based on the command specified from the CLI argument parser.

    Each method in the dispatcher registers a `cli.parser.Command` enum
    type to perform a task based on the cli command.

    Note:
        If the `cli.parser.Command` is extended with new commands, a
        method to handle said new command type should be made here to
        handle it properly.
    """
    # Class registry used to register class methods to
    # `cli.parser.Command` enum types
    _REGISTRY = utils.Registry()

    def __init__(self, pydev_container: container.PyDevContainer) -> None:
        self._pydev_container = pydev_container

    @_REGISTRY.register_callable(cli.parser.Command.RUN)  # type: ignore
    def run(self, options: pydev_docker.options.ContainerOptions):
        """
        Dispatches the `cli.parser.Command.RUN` command which invokes
        `container.PyDevContainer.run` with options retrieved from the CLI.

        Note:
            This method will print the results from `container.PyDevContainer.run`
            to STDOUT

        Args:
            options: The container options used to pass arguments to
                the `container.PyDevContainer.run` method.
        """
        result = self._pydev_container.run(
            image=options.image,
            command=options.command,
            volumes=options.get_volume_collection(),
            environment=options.get_environment_collection(),
            network=options.network,
            ports=options.get_ports(),
            remove=options.remove_container,
        )
        for r in result:
            sys.stdout.write(r.decode())

    @_REGISTRY.register_callable(cli.parser.Command.RUN_PTY)  # type: ignore
    def run_pty(self, options: pydev_docker.options.ContainerOptions):
        """
        Dispatches the `cli.parser.Command.RUN_PTY` command which invokes
        `container.PyDevContainer.run_pty` with options retrieved from the CLI.

        Args:
            options: The container options used to pass arguments to the
                container.PyDevContainer.run_pty method.
        """
        self._pydev_container.run_pty(
            image=options.image,
            command=options.command,
            volumes=options.get_volume_collection(),
            environment=options.get_environment_collection(),
            network=options.network,
            ports=options.get_ports(),
            remove=options.remove_container,
        )

    def dispatch(self, command: cli.parser.Command,
                 options: pydev_docker.options.ContainerOptions):
        """
        Dispatches the correct command to execute based on the `command` enum
        using the `options` provided.

        Args:
            command: The command to execute
            options: The container options passed to the method being invoked

        Returns:
            The result of the dispatched method

        Raises:
            DispatcherError: If the key provided was invalid, this would only occur due
                to programmer error (not implementing a dispatcher method based on
                the `cli.parser.Command` enum)
            container.ContainerError: If there was an error while invoking a method from
                `container.PyDevContainer`
        """
        try:
            func = self._REGISTRY.get(command)  # type: ignore
        except utils.RegistryKeyError:
            raise DispatcherError(
                "Command {} has not been registered with the dispatcher".format(command)
            )
        return func(self, options)


def setup_logger(verbosity: cli.parser.Verbosity):
    verbosity_map = {
        cli.parser.Verbosity.DEBUG: logging.DEBUG,
        cli.parser.Verbosity.INFO: logging.INFO,
        cli.parser.Verbosity.WARN: logging.WARN,
    }
    # TODO: Allow option to log to file instead of stdout
    logging.basicConfig(
        level=verbosity_map[verbosity],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt='%m-%d %H:%M:%S',
        stream=sys.stdout,
    )


def print_exception(msg: Exception):
    print(msg, file=sys.stderr)


def main():
    try:
        arguments = cli.parser.parse_args()
    except cli.parser.ParseError as e:
        print_exception(e)
        return 1

    setup_logger(arguments.verbosity)

    try:
        docker_client = docker.from_env()
    except docker.errors.DockerException as e:
        print_exception(e)
        return 1

    pydev_container = container.PyDevContainer(docker_client)
    dispatcher = CommandDispatcher(pydev_container)

    try:
        dispatcher.dispatch(arguments.command, arguments.container_options)
    except DispatcherError as e:
        print_exception(e)
        return 1
    except container.ContainerError as e:
        print_exception(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
