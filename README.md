#Overview
A simple [ultramemcached](https://github.com/esnme/ultramemcached) cache backend for Django.


#Notes
This cache backend requires the [ultramemcache](https://github.com/esnme/ultramemcache) Python client library for
communicating with the Memcached server.

#Usage
```python
On Django >= 1.3::

    CACHES = {
        'default': {
            'BACKEND': 'ultramemcached-cache.UltraMemcachedCache',
            'LOCATION': ['<host>:<port>',],
            'TIMEOUT: 60*60*24*30,
        },
    }
```