import abc
import collections
from fused.model import Model
from . import storage


class Item(Model):
    redis = storage.get_main_connection()