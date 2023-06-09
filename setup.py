
from setuptools import setup

with open("README.md") as f:
    README = f.read()

setup(
    name='python-bindiff',
    version='0.1.1',
    description='Python wrapper to manipulate bindiff files',
    author='Robin David',
    author_email='rdavid@quarkslab.com',
    url='https://github.com/quarkslab/python-bindiff',
    long_description_content_type='text/markdown',
    long_description=README,
    packages=['bindiff'],
    project_urls={
        "Documentation": "https://quarkslab.github.io/diffing-portal/differs/bindiff.html#python-bindiff",
        "Bug Tracker": "https://github.com/quarkslab/python-bindiff/issues",
        "Source": "https://github.com/quarkslab/python-bindiff"
    },
    python_requires='>=3.9',
    install_requires=[
        'python-magic',
        'click',
        'python-binexport'
    ],
    license="AGPL-3.0",
    classifiers=[
        'Topic :: Security',
        'Environment :: Console',
        'Operating System :: OS Independent',
    ],
    scripts=['bin/bindiffer']
)
