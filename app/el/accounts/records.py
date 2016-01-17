from ... import consts
from ..misc import abc, utils
import time
from fused import fields
from functools import partialmethod


class Record(abc.Item):

    name = fields.String(unique=True, required=True)
    pwd = fields.Bytes(required=True)
    email = fields.String(unique=True)
    real_name = fields.String() 
    fixed_post = fields.Foreign('Post')
    avatar = fields.Foreign('Image')
    # Sorted sets of primary keys
    images = fields.SortedSet(standalone=True)
    posts = fields.SortedSet(standalone=True)
    followers = fields.SortedSet(standalone=True)
    following = fields.SortedSet(standalone=True)
    friends = fields.SortedSet(standalone=True)
    notifications = fields.SortedSet(standalone=True)

    def _add(self, field, value, score=None):
        if score is None:
            score = time.time()
        encoded = self.encode(fields.PrimaryKey, value)
        return getattr(self, field).zadd(score, encoded)

    def _delete(self, field, value):
        encoded = self.encode(fields.PrimaryKey, value)
        return getattr(self, field).zrem(encoded)

    def _get(self, field, min='-inf', max='+inf', **ka):
        raw = getattr(self, field).zrangebyscore(min, max, **ka)
        yield from (self.decode(fields.PrimaryKey, x) for x in raw)

    # Common ops for above sorted sets
    add_image = partialmethod(_add, 'images')
    delete_image = partialmethod(_delete, 'images')
    get_images = partialmethod(_get, 'images')

    add_post = partialmethod(_add, 'posts')
    delete_post = partialmethod(_delete, 'posts')
    get_posts = partialmethod(_get, 'posts')

    add_follower = partialmethod(_add, 'followers')
    delete_follower = partialmethod(_delete, 'followers')
    get_followers = partialmethod(_get, 'followers')

    add_following = partialmethod(_add, 'following')
    delete_following = partialmethod(_delete, 'following')
    get_following = partialmethod(_get, 'following')

    add_friend = partialmethod(_add, 'friends')
    delete_friend = partialmethod(_delete, 'friends')
    get_friends = partialmethod(_get, 'friends')

    add_notification = partialmethod(_add, 'notifications')
    delete_notification = partialmethod(_delete, 'notifications')
    get_notifications = partialmethod(_get, 'notifications')