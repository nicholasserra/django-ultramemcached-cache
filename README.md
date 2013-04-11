#Warning
A better solution to this backend might be to drop in my [python-ultramemcache](https://github.com/nicholasserra/python-ultramemcached) library and make your own backend:



```python
from django.core.cache.backends.memcached import BaseMemcachedCache

class UltraMemcachedCache(BaseMemcachedCache):
    "An implementation of a cache binding using python-ultramemcached"
    def __init__(self, server, params):
        import ultramemcache
        super(MemcachedCache, self).__init__(server, params,
                                             library=ultramemcache,
                                             value_not_found_exception=ValueError)
```

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
