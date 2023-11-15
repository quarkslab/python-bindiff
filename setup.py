from setuptools import setup

setup(
    packages=find_packages(
        where="src",
        include=["bindiff*"],
    ),
    scripts=["bin/bindiffer"],
)
