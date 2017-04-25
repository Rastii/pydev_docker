import setuptools
import codecs
from os import path


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with codecs.open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


setuptools.setup(
    name="pydev_docker",
    version="0.0.1",
    description="Docker python development container deployment with pythonpath auto mounting",
    long_description=long_description,
    url="https://github.com/Rastii/pydev_docker",
    author="Luke Hritsko",
    license="MIT",
    # TODO
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
    ],
    keywords="docker dev develop environment",
    # TODO: If docs / tests are added then exclude them!
    packages=setuptools.find_packages(exclude=["docs"]),
    entry_points={
        "console_scripts": [
            "pydev_docker=pydev_docker.cli.runner:main",
        ],
    },
    install_requires=[
        "docker>=2.2.1",
        "dockerpty>=0.4.1",
        "PyYAML>=3.12",
    ],
    extras_require={
        "lint": [
            "flake8>=3.3.0",
            "mypy>=0.501",
        ]
    }
)
