import abc
import collections
from fused.model import Model
from fused.fields import PrimaryKey
from . import storage
import time

import redis

class Item(Model):
    redis = storage.get_main_connection()
    id = PrimaryKey()
    @classmethod
    def new(cls, **ka):
        if 'id' not in ka:
            # FIXME:
            ka['id'] = str(time.time())
        return super().new(**ka)