PyDev Docker
^^^^^^^^^^^^

Work on multiple python packages in the same docker container with ease.

PyDev Docker will automatically mount multiple python packages on the container
and make the packages accessible via PYTHONPATH environment variable.

Examples
========

Run a command on a docker container mounting the current directory as the "source"
directory using the "py3_dev" docker image:

.. code-block:: bash

    $ pydev_docker run py3_dev "python3 setup.py test"


Spawn an interactive PTY shell on the docker container mounting the current
directory as the "source" directory using the "py3_dev" docker image:

.. code-block:: bash

    $ pydev_docker run_pty py3_dev


Mounting Additional Python Packages
-----------------------------------

Mount "NetworkPackage" and "FilePackage" that will be appended to the $PYTHONPATH
environment variable and run a command using the image "py3_dev":


.. code-block:: bash

    $ pydev_docker run -g ~/Projects/NetworkPackage \
                       -g ~/Projects/FilePackage \
                       py3_dev "python3 setup.py test"


Or, we could add these to ``config.yml``:

.. code-block:: yaml

    python_packages:
        - ~/Projects/NetworkPackage
        - ~/Projects/FilePackage

And run the command specifying the config file:

.. code-block:: bash

    $ pydev_docker run --config config.yml py3_dev "python3 setup.py test"


Configuration File Settings
===========================

The configuration file is a YAML dictionary with two attributes: ``python_packages`` and
``docker_options``.

Python Packages Section
-----------------------

The **python_packages** section supports the following settings:

- **container_directory** (*string*): The directory in which the additional python packages will
  be mounted to in the docker container. Defaults to ``/pypath``.
- **paths** (*list*): A list of paths that are python packages.  Note that this *must* be a path
  of a python package (contains __init__.py).

Example:

.. code-block:: yaml

    python_packages:
        container_directory: "/more_py"
        paths:
            - ~/Projects/NetworkPackage/network_package
            - /home/dingle/OpenSource/MagicPackage/magic_package

Note: user paths will get expanded and relative paths are relative from the location in which
the script was invoked.

Docker Options Section
----------------------

The **docker_options** section attempts to closely mimic the syntax of docker-compose files.
It contains the following settings:

- **environment** (*dictionary*): Specifies the environment variables that will be configured
  on the docker container.  Note that ``PYTHONPATH`` will be automatically configured and should
  **not** be used here.

- **network** (*string*): Specifies a network to connect the container to.  Defaults
  to the default bridge network.

- **ports** (*list*): Specifies a list of ``HOST_PORT[:CONTAINER_PORT]`` port mappings where
  HOST_PORT is the port that will be opened on the host and the CONTAINER_PORT is the port
  that will be opened on the container.

- **volumes** (*list*): List of ``HOST_LOCATION:CONTAINER_LOCATION[:MODE]`` strings where
  HOST_LOCATION is the location of the volume on the host, CONTAINER_LOCATION is where to mount
  the volume on the container and MODE specifies the mount mode of the volume: ro (Read-Only) or
  rw (Read-Write), defaults to **rw**.


Example:

.. code-block:: yaml

    docker_options:
        environment:
            UTIL_PATH: /utils
            TEST_DB_USER: foo_user
            TEST_DB_PASS: test_foo_user_pass
        network: network_with_db
        ports:
            - "80:8080"
            - 443
        volumes:
            - ~/my/utils:/utils:ro


Installation
============

To install from github, please use the following commands:

.. code-block:: bash

    $ git clone https://github.com/rastii/pydev_docker.git
    $ cd pydev_docker
    $ python setup.py build
    $ sudo python setup.py install

After following the commands, the ``pydev_docker`` command should be installed.
