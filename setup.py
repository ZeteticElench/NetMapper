"""Setup script for NetMapper."""

from setuptools import setup, find_packages

setup(
    name="netmapper",
    version="1.0.0",
    description="Network topology discovery using PyATS and Neo4j",
    author="NetMapper Contributors",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "pyats>=24.0",
        "genie>=24.0",
        "neo4j>=5.14.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0",
        "typing-extensions>=4.8.0",
    ],
    entry_points={
        "console_scripts": [
            "netmapper=netmapper.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Networking",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
