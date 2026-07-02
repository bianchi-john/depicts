from setuptools import setup, find_packages
import os

# Get version from __init__.py
version = {}
with open(os.path.join("depicts", "__init__.py")) as f:
    exec(f.read(), version)

setup(
    name='depicts',
    version=version['__version__'],
    packages=find_packages(),
    install_requires=[
        'PyYAML',
    ],
    entry_points={
        'console_scripts': [
            'depicts=depicts.cli:main',
        ],
    },
)
