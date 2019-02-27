from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(
    name='ckanext-validator',
    version=version,
    description="Data validation for CKAN",
    long_description="""
    """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Fjelltopp',
    author_email='',
    url='http://fjelltopp.org',
    license='GPL v3.0',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
	# -*- Extra requirements: -*-
    ],
    entry_points="""
    [ckan.plugins]
    # Add plugins here, eg
    validator=ckanext.validator.plugin:ValidatorPlugin
    """,
)
