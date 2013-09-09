#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""

"""
__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '29.04.13 - 15:34'

from setuptools import setup

setup(
    name='Tornado-Restless',
    version='0.3.2',
    author='Martin Martimeo',
    author_email='martin@martimeo.de',
    url='https://github.com/MartinMartimeo/tornado-restless',
    packages=['tornado_restless'],
    license='GNU AGPLv3+',
    platforms='any',
    description='flask-restless adopted for tornado',
    long_description=open('README.md').read(),
    install_requires=open('requirements.txt').readlines(),
    test_suite='nose.collector',
    tests_require=open('requirements-test.txt').readlines(),
    download_url='http://pypi.python.org/pypi/Tornado-Restless',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)