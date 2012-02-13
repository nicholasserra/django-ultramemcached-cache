#!/usr/bin/env python

from setuptools import setup

setup(
    name='ultramemcached-cache',
    version='0.0.1',
    install_requires=['umemcache'],
    author='Nicholas Serra',
    author_email='nick@528hazelwood.com',
    license='MIT License',
    url='https://github.com/nicholasserra/django-ultramemcached-cache/',
    keywords='python memcache memcached ultramemcache django cache backend',
    description='A django cache backend using ultramemcache',
    long_description=open('README.md').read(),
    download_url="https://github.com/nicholasserra/django-ultramemcached-cache/zipball/master",
    py_modules=["ultramemcached-cache"],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet'
    ]
)