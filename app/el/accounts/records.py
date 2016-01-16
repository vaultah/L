from ... import consts
from ..misc import abc, utils
import collections
import time
from fused import fields
from functools import partialmethod


def add(model, field, value, score=None):
    if score is None:
        score = time.time()
    encoded = model.encode(fields.PrimaryKey, value)
    return getattr(model, field).zadd(score, encoded)


def delete(model, field, value):
    encoded = model.encode(fields.PrimaryKey, value)
    return getattr(model, field).zrem(encoded)


class Record(abc.Item):

    name = fields.String(unique=True, required=True)
    pwd = fields.Bytes(required=True)
    email = fields.String(unique=True)
    real_name = fields.String() 
    fixed_post = fields.Foreign('Post')
    # Sorted sets of primary keys
    images = fields.SortedSet(standalone=True)
    posts = fields.SortedSet(standalone=True)
    followers = fields.SortedSet(standalone=True)
    following = fields.SortedSet(standalone=True)
    friends = fields.SortedSet(standalone=True)
    notifications = fields.SortedSet(standalone=True)

    # Common ops for above sorted sets
    add_image = partialmethod(add, 'images')
    delete_image = partialmethod(delete, 'images')

    add_post = partialmethod(add, 'posts')
    delete_post = partialmethod(delete, 'posts')

    add_follower = partialmethod(add, 'followers')
    delete_follower = partialmethod(delete, 'followers')

    add_following = partialmethod(add, 'following')
    delete_following = partialmethod(delete, 'following')

    add_friend = partialmethod(add, 'friends')
    delete_friend = partialmethod(delete, 'friends')

    add_notification = partialmethod(add, 'notifications')
    delete_notification = partialmethod(delete, 'notifications')