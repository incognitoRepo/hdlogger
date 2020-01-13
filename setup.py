# -*- coding: utf-8 -*-

# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='hdlogger',
    version='0.1.0',
    description='Sample package for Python-Guide.org',
    long_description=readme,
    author='Albert Han',
    author_email='incognitoRepo@outlook.com',
    url='https://github.com/incognitoRepo/hdlogger',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)

