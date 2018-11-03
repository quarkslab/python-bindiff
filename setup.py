
from setuptools import setup

setup(
    name='python-bindiff',
    version='0.1',
    description='Python wrapper to manipulate bindiff files',
    author='Robin David',
    author_email='rdavid@quarkslab.com',
    url='https://gitlab.qb/rdavid/python-bindiff',
    packages=['bindiff'],
    install_requires=[
        'python-magic',
        'click',
        'python-binexport'
    ],
    scripts=['bin/bindiffer']
)
