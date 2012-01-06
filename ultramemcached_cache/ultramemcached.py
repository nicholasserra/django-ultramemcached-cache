"UltraMemcached cache backend"

import time
from threading import local

from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.utils import importlib

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    from zlib import compress, decompress
    _supports_compress = True
except ImportError:
    _supports_compress = False
    # quickly define a decompress just in case we recv compressed data.
    def decompress(val):
        raise _Error("received compressed data but I don't support compression (import error)")

_FLAG_PICKLE  = 1<<0
_FLAG_INTEGER = 1<<1
_FLAG_LONG    = 1<<2
_FLAG_COMPRESSED = 1<<3

class BaseUltraMemcachedCache(BaseCache):
    def __init__(self, server, params, library, value_not_found_exception):
        super(BaseUltraMemcachedCache, self).__init__(params)
        
        if isinstance(server, basestring):
            self._servers = server.split(';')[0]
        else:
            self._servers = server[0]

        # The exception type to catch from the underlying library for a key
        # that was not found. This is a ValueError for python-memcache,
        # pylibmc.NotFound for pylibmc, and cmemcache will return None without
        # raising an exception.
        self.LibraryValueNotFoundException = value_not_found_exception

        self._lib = library
        self._options = params.get('OPTIONS', None)
        self.pickler = pickle.Pickler
        self.unpickler = pickle.Unpickler
        self.pickleProtocol = 0
        
        try:
            pickler = self.pickler(file, protocol = self.pickleProtocol)
            self.picklerIsKeyword = True
        except TypeError:
            self.picklerIsKeyword = False

    @property
    def _cache(self):
        """
        Implements transparent thread-safe access to a memcached client.
        """
        self._client = self._lib.Client(self._servers)
        return self._client

    def _make_conn(func, *args, **kwargs):
        def wrapper(self, *args, **kwargs):
            client = self._cache
            client.connect()
            return func(self, client, *args, **kwargs)
            client.disconnect()
        return wrapper

    def _get_memcache_timeout(self, timeout):
        """
        Memcached deals with long (> 30 days) timeouts in a special
        way. Call this function to obtain a safe value for your timeout.
        """
        timeout = timeout or self.default_timeout
        if timeout > 2592000: # 60*60*24*30, 30 days
            # See http://code.google.com/p/memcached/wiki/FAQ
            # "You can set expire times up to 30 days in the future. After that
            # memcached interprets it as a date, and will expire the item after
            # said date. This is a simple (but obscure) mechanic."
            #
            # This means that we have to switch to absolute timestamps.
            timeout += int(time.time())
        return timeout

    def _val_to_store(self, val, min_compress_len=0):
        flags = 0
        if isinstance(val, str):
            pass
        elif isinstance(val, int):
            flags |= _FLAG_INTEGER
            val = "%d" % val
            # force no attempt to compress this silly string.
            min_compress_len = 0
        elif isinstance(val, long):
            flags |= _FLAG_LONG
            val = "%d" % val
            # force no attempt to compress this silly string.
            min_compress_len = 0
        else:
            flags |= _FLAG_PICKLE
            file = StringIO()
            if self.picklerIsKeyword:
                pickler = self.pickler(file, protocol = self.pickleProtocol)
            else:
                pickler = self.pickler(file, 0)
            pickler.dump(val)
            val = file.getvalue()
            
        lv = len(val)
        # We should try to compress if min_compress_len > 0 and we could
        # import zlib and this string is longer than our min threshold.
        
        if min_compress_len and _supports_compress and lv > min_compress_len:
            print 'in compress'
            comp_val = compress(val)
            # Only retain the result if the compression result is smaller
            # than the original.
            if len(comp_val) < lv:
                print 'set compress flags'
                flags |= _FLAG_COMPRESSED
                val = comp_val

        return val, flags
    
    def _clean_val(self, buf, flags, default=None):
        if flags & _FLAG_COMPRESSED:
            buf = decompress(buf)
        if  flags == 0 or flags == _FLAG_COMPRESSED:
            # Either a bare string or a compressed string now decompressed...
            val = buf
        elif flags & _FLAG_INTEGER:
            val = int(buf)
        elif flags & _FLAG_LONG:
            val = long(buf)
        elif flags & _FLAG_PICKLE:
            try:
                file = StringIO(buf)
                unpickler = self.unpickler(file)
                val = unpickler.load()
            except Exception, e:
                val = None
        else:
            return default
        return val
        
    @_make_conn
    def add(self, client, key, val, timeout=0, version=None, min_compress_len=0):
        key = self.make_key(key, version=version)
        val, flags = self._val_to_store(val, min_compress_len)
        stored = client.add(key, val, self._get_memcache_timeout(timeout), flags)
        return stored == "STORED"

    @_make_conn
    def get(self, client, key, default=None, version=None):
        key = self.make_key(key, version=version)
        response = client.get(key)

        if not response:
            return default

        value = self._clean_val(response[0], response[1])
        return value

    @_make_conn
    def set(self, client, key, val, timeout=0, version=None, min_compress_len=0):
        key = self.make_key(key, version=version)
        val, flags = self._val_to_store(val, min_compress_len)
        stored = client.set(key, val, self._get_memcache_timeout(timeout), flags)
        return stored == "STORED"
        
    @_make_conn
    def delete(self, client, key, version=None):
        key = self.make_key(key, version=version)
        client.delete(key)

    @_make_conn
    def get_many(self, client, keys, default=None, version=None):
        if not isinstance(keys, (list, tuple)):
            raise TypeError
        
        new_keys = map(lambda x: self.make_key(x, version=version), keys)
        ret = client.get_multi(new_keys)
        if ret:
            _ = {}
            m = dict(zip(new_keys, keys))
            for k, v in ret.items():
                value = self._clean_val(v[0], v[1])
                _[m[k]] = value
            ret = _
        return ret

    def close(self, **kwargs):
        return

    @_make_conn
    def incr(self, client, key, delta=1, version=None):
        key = self.make_key(key, version=version)
        try:
            val = client.incr(key, delta)

        # python-memcache responds to incr on non-existent keys by
        # raising a ValueError, pylibmc by raising a pylibmc.NotFound
        # and Cmemcache returns None. In all cases,
        # we should raise a ValueError though.
        except self.LibraryValueNotFoundException:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    @_make_conn
    def decr(self, client, key, delta=1, version=None):
        key = self.make_key(key, version=version)
        try:
            val = client.decr(key, delta)

        # python-memcache responds to incr on non-existent keys by
        # raising a ValueError, pylibmc by raising a pylibmc.NotFound
        # and Cmemcache returns None. In all cases,
        # we should raise a ValueError though.
        except self.LibraryValueNotFoundException:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    @_make_conn
    def set_many(self, client, data, timeout=0, version=None, min_compress_len=0):
        #not any faster because there is no set_many in umemcached

        if not isinstance(data, dict):
            raise TypeError
            
        safe_data = {}

        for key, value in data.items():
            key = self.make_key(key, version=version)
            safe_data[key] = value

        for key, val in safe_data.items():
            final_value, flags = self._val_to_store(val, min_compress_len)

            client.set(key, final_value, self._get_memcache_timeout(timeout), flags)

    @_make_conn
    def delete_many(self, client, keys, version=None):
        #not any faster because there is no delete_many in umemcached

        if not isinstance(keys, (list, tuple)):
            raise TypeError

        l = lambda x: self.make_key(x, version=version)
        for key in map(l, keys):
            client.delete(key)

class UltraMemcachedCache(BaseUltraMemcachedCache):
    "An implementation of a cache binding using umemcached"
    def __init__(self, server, params):
        import umemcached
        super(UltraMemcachedCache, self).__init__(server, params,
                                             library=umemcached,
                                             value_not_found_exception=ValueError)