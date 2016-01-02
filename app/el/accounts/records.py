from ... import consts
from ..misc import abc, utils
import collections
from fused import fields


class Record(abc.Item):
    name = fields.String(unique=True, required=True)
    pwd = fields.Bytes(required=True)
    email = fields.String(unique=True)
    real_name = fields.String()
    fixed_post = fields.Foreign('Post')
    images = fields.SortedSet()
    posts = fields.SortedSet()
    followers = fields.SortedSet()
    following = fields.SortedSet()
    friends = fields.SortedSet()