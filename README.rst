==========================
Ultramemcached Django Cache Backend
==========================

A simple Ultramemcached cache backend for Django

Notes
-----

This cache backend requires the `ultramemcached`_ Python client library for
communicating with the Memcached server.

Usage
-----
On Django >= 1.3::

    CACHES = {
        'default': {
            'BACKEND': 'ultramemcached_cache.ultramemcached.UltraMemcachedCache',
            'LOCATION': ['<host>:<port>',],
            'TIMEOUT: 60*60*24*30,
        },
    }

.. _ultramemcached: https://github.com/esnme/ultramemcached/