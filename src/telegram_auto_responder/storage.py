# -*- coding: utf-8 -*-

import os
import json
import threading


class Storage(object):
    _lock = threading.Lock()

    def lock(f):
        def w(*a, **kw):
            kw.setdefault('skip_lock', False)
            sl = kw.get('skip_lock')
            del kw['skip_lock']

            if sl:
                Storage._lock.acquire()
            try:
                r = f(*a, **kw)
            except:
                import traceback
                traceback.print_exc()

            if sl:
                Storage._lock.release()

            return r

        return w

    def __init__(self, path):
        self._path = os.path.join(path, 'c.db')

        # create
        self._lock.acquire()
        if not os.path.isfile(self._path):
            with file(self._path, 'wb') as f:
                json.dump(dict(), f)

        self._lock.release()

    @lock
    def get(self, k=None, default=None):
        d = None
        with file(self._path) as f:
            try:
                d = json.load(f)
            except ValueError:
                return default

        if k is None:
            return d

        return d.get(k, default)

    @lock
    def set(self, k, v):
        d = self.get(default=dict(), skip_lock=True)
        d[k] = v
        with file(self._path, 'wb') as f:
            json.dump(d, f)

        return
