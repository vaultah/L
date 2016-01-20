from . import  wsinter
from .accounts.profile import profile
from .accounts import relations, records
from .. import consts
from .misc import abc, utils
from .images import Image
from datetime import datetime
from itertools import chain
from collections import ChainMap, deque
import collections.abc
import threading
# For PUSH post loading purposes
import jinja2
from fused import fields


class Post(abc.Item):
    type = consts.CONTENT_POST
    owner = fields.Foreign(records.Record, required=True)
    content = fields.String()
    base_post = fields.Foreign('Post')
    base_image = fields.Foreign('Image')
    derived = fields.SortedSet(standalone=True)

    @property
    def base(self):
        return self.base_post or self.base_image

    def is_reply(self):
        return self.base and (self.content or self.images)

    def get_derived(self):
        raw = self.derived.zrange(0, -1)
        yield from (self.decode(fields.PrimaryKey, x) for x in raw)

    # @classmethod
    # def delete(cls, acct, posts):
    #     ''' Most of deleting actions are delayed (e.g. `delete_tree` in
    #         `branch`); this method makes as little changes as possible '''
    #     if not isinstance(acct, records.Record):
    #         raise TypeError

    #     if not posts:
    #         raise ValueError('Nothing to delete')

    #     ins = list(cls.instances(posts))
    #     # Make a list excluding the posts not belonging to `acct`
    #     valid = [x for x in ins if x.owner == acct]
    #     super
    #     threading.Thread(target=Feed.delete, kwargs={'posts': ins},
    #                      daemon=True).start()

    @classmethod
    def new(cls, feed=True, **ka):
        if not any([ext and ext.good, content and not content.isspace(), images]):
            raise ValueError('Post is empty')

        if not isinstance(poster, records.Record):
            raise TypeError

        if images and not isinstance(images[0], Image):
            raise TypeError

        if ext:
            # Type checking is mandatory: `Image` can't have base field, etc.
            if isinstance(ext, Post) and not (ext.content or ext.images):
                # It's a reflection, fall back to its base
                ext = ext.base
            else:
                ext = [ext.id, ext.type]

        # TODO: ext.good()?

        # This goes to the DB
        data = {'images': [x.id for x in images] if images else None,  
                'owner': poster.id,
                'content': content if content or images else None,
                'base': ext or None,
                'score': 0}

class Feed:

    @classmethod
    def new(cls, posts, ids):
        # Accept iterable of instances or a single instance
        # Checking for instance type would require the consumption of the 
        # iterable
        try:
            posts = iter(posts)
        except TypeError:
            posts = [posts]
        # We could use BulkSomethingSomething, but seems like MongoDB
        # uses BulkSomethingSomething implicitly when an array of documents 
        # submitted. Too lazy to check what does PyMongo do in this case.
        # TODO: Think if we need to use bulk ops instead
        many = [{'post': post.id, 'acct': x.id} for post in posts for x in ids]
        cls.collection.insert_many(many)

    @classmethod
    def delete(cls, posts=(), ids=()):
        
        spec = {}
        if posts:
            try:
                posts = list(posts)
            except TypeError:
                posts = [posts]
            finally:
                if not isinstance(posts[0], Post):
                    raise ValueError('We expect Post instances') from None
                spec['post'] = {'$in': [post.id for post in posts]}

        if ids:
            try:
                ids = list(ids)
            except TypeError:
                ids = [ids]
            finally:
                if not isinstance(ids[0], records.Record):
                    raise ValueError('We expect records.Record instances') from None
                spec['acct'] = {'$in': [rec.id for rec in ids]}

        cls.collection.delete_many(spec)

    @classmethod
    def get(cls, acct, number=25, start=None):
        if not isinstance(acct, records.Record):
            raise TypeError

        if start and type(start) is not ObjectId:
            raise TypeError

        params = {'acct': acct.id}
        if start:
            params.update(post={'$lt': start})

        cur = cls.collection.find(params).limit(number).sort([('$natural', -1)])
        yield from (Post(x['post']) for x in cur)


# FIXME: New followers/friends -> feedgetters






def push(post, tpl, **ka):
    # Doing the real push here
    if not isinstance(tpl, jinja2.Template):
        raise TypeError

    # Different markup for current and others (to correctly
    # display Spam/Delete buttons)
    ka.update(posts=iter_info([post]))
    # Render the template for current
    args = ({'action': 'feed', 'ids': (post.owner.id,), 
             'markup': tpl.render(ka)},)
    threading.Thread(target=wsinter.async_send, args=args, daemon=True).start()
    # Render the template for others
    ka['push'] = True
    args = ({'action': 'feed', 'ids': relations.feedgetters(post.owner),
             'markup': tpl.render(ka)},)
    threading.Thread(target=wsinter.async_send, args=args, daemon=True).start()


def derived(item, shared=False):
    if not item.good():
        raise ValueError('The post/image does not exist')
    replies = [item]
    while replies:
        yield replies
        derived = chain.from_iterable(x.get_derived() for x in replies)
        replies = [x for x in Post.instances(derived)
                     if x.good() and (shared or x.is_reply())]


def delete_tree(item):
    ''' Delete replies and shared items '''
    for x in chain(*derived(item, shared=True)):
        # TODO: x.owner.good()?
        x.owner.delete_post(x)
        x.delete()

    
def parents(item):
    # Can't evaluate lazily, will be generator anyway
    if not item.good():
        raise ValueError('The post/image does not exist')

    items = [item]
    while True:
        if not items[-1].good():
            delete_tree(items[-2])
            items[:] = []
            break

        if not items[-1].base:
            break

        if items[-1].base[-1] == Post.type:
            obj = Post(items[-1].base[0])
        else:
            obj = Image(items[-1].base[0])

        items.append(obj)

    # Output as 
    #   base -> first order reply -> ... -> `item`
    items.reverse()
    yield from items


def level_info(levels):
    profiles = {}
    for level in levels:
        yield iter_info(level, profiles=profiles)


def iter_info(iterable, profiles=None):
    if profiles is None:
        profiles = {}

    if not isinstance(iterable, collections.abc.Sequence):
        iterable = list(iterable)

    for post in iterable:
        if not post.good():
            continue
        if post.owner.id not in profiles:
            profiles[post.owner.id] = profile(post.owner)

        # Add data to the instance
        time, temp = int(datetime.timestamp(post.id.generation_time)), {}
        temp['profile'] = profiles[post.owner.id]
        temp['passed'] = utils.gettime(time)
        temp['time'] = utils.full_date(time)

        if isinstance(post, Post):
            if post.content:
                temp['content'] = utils.urls(post.content)

            if post.images:
                temp['images'] = [(x, utils.image_url(name=x.name, type=consts.SHRINKED_IMAGE))
                                   for x in map(Image, post.images)]

        post.add(temp)

    return iterable
