from . import  wsinter
from .accounts.profile import profile
from .accounts.records import Record
from .accounts import relations
from .. import consts
from .misc import abc, utils
from .images import Image
from datetime import datetime
import itertools
from bson.objectid import ObjectId
from pymongo.cursor import CursorType
from pymongo import MongoClient
from collections import ChainMap, deque
import collections.abc
import threading
# For PUSH post loading purposes
import jinja2

client = MongoClient()


def _post_link(id):
    return '/survey/post/{}'.format(id)


class Post(abc.Scorable, abc.Item):

    ''' Represents a single post 

        All published items are represented with this class '''

    type = consts.CONTENT_POST
    _db, _collection = consts.MONGO['posts']
    collection = client[_db][_collection]


    def __init__(self, post=None):
        self._fields = {}
        self.derived = []
        if post:
            post = ObjectId(post)
            result = self.collection.find_one({self.pk: post}) or {}
            if 'owner' in result:
                result['owner'] = Record(id=result['owner'])
            self._init_setfields(self, result)

    def _prepare(self):
        if self.owner and not isinstance(self.owner, Record):
            self._setfields(self, {'owner': Record(id=self.owner)})

    def is_reply(self):
        return self.base and (self.content or self.images)

    @classmethod
    def delete(cls, acct, posts):
        ''' Most of deleting actions are delayed (e.g. `delete_derived` in
            `branch`); this method makes as little changes as possible '''
        if not isinstance(acct, Record):
            raise TypeError

        if not posts:
            raise ValueError('Nothing to delete')

        ins = list(cls.instances(posts))
        # Make a list excluding the posts not belonging to `acct`
        valid = [x for x in ins if x.owner == acct]

        threading.Thread(target=Feed.delete, kwargs={'posts': ins},
                         daemon=True).start()

        with acct:
            op = cls.collection.delete_many({cls.pk: {'$in': [x.id for x in valid]}})
            acct.posts -= op.deleted_count

    @classmethod
    def new(cls, poster, content=None, ext=None, images=None, feed=True):
        if (not (ext and ext.good()) and
            not (content and not content.isspace()) and 
            not images):
            raise ValueError('Post is empty')

        if not isinstance(poster, Record):
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

        data['id'], data['hash'] = utils.unique_id()

        # Don't write `None` fields to a document
        data = {x: y for x, y in data.items() if y is not None}
        cls.collection.insert_one(data)
        with poster:
            poster.posts += 1
        data['owner'] = poster
        
        # Create the post instance from the dictionary
        instance = cls.fromdata(data)

        # if feed:
        #     ids = (poster,) + relations.feedgetters(poster)
        #     th = threading.Thread(target=Feed.new, args=(instance, ids), daemon=True)
        #     th.start()

        return instance

    def __repr__(self):
        pat = ('<Post object at {addr:#x}: {self.pk}={self.id!r} images={images} '
               'base={self.base}>')
        mapping = {'addr': id(self), 'self': self, 'images': len(self.images or ())}
        return pat.format_map(mapping)


class Feed:

    _db, _collection = consts.MONGO['feed']
    collection = client[_db][_collection]

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
                if not isinstance(ids[0], Record):
                    raise ValueError('We expect Record instances') from None
                spec['acct'] = {'$in': [rec.id for rec in ids]}

        cls.collection.delete_many(spec)

    @classmethod
    def get(cls, acct, number=25, start=None):
        if not isinstance(acct, Record):
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

def total():
    return Post.collection.count()


def derived(item, reflections=False):
    if not item.good():
        raise ValueError('The post does not exists')
    # Refillable list of replies of any type
    replies = [item]
    # Common selectors
    spec = ChainMap({})

    while replies:
        temp, bases = [], [[x.id, x.type] for x in replies]
        derivations = {(x.id, x.type): x.derived for x in replies}
        kw = {'filter': spec.new_child({'base': {'$in': bases}}),
              'cursor_type': CursorType.EXHAUST}
 
        # Applies to posts only
        if not reflections:
            kw['filter'] = kw['filter'].new_child({'$or': [
                {'content': {'$exists': True}},
                {'images': {'$exists': True}}
            ]})

        kw['filter'] = dict(kw['filter'])

        for document in Post.collection.find(**kw):
            v = Post.fromdata(document)
            derivations[tuple(v.base)].append(v)
            temp.append(v)

        yield replies

        replies = temp


def delete_derived(item):
    ''' Delete replies and reflections '''
    chained = itertools.chain(*derived(item, reflections=True))
    # Technically, it would be correct to remove the first element
    # because "item is next(chained)", but I'll advance the iterator and
    # free item.derived at the same time
    Post.collection.delete_many({Post.pk: {'$in': [x.id for x in chained]}})

    
def parents(item):
    # Can't evaluate lazily, will be generator anyway
    if not item.good():
        raise ValueError('The post/image does not exists')

    items = [item]
    while True:
        if not items[-1].good():
            delete_derived(items[-2])
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


def page(poster, number=50):
    if not isinstance(poster, Record):
        raise TypeError
        
    params = {'owner': poster.id}
    cur = Post.collection.find(params).limit(number).sort([('$natural', -1)])
    yield from (Post.fromdata(x) for x in cur)