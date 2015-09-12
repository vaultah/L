import enum
import warnings
from collections import ChainMap
from .misc import utils, abc
from .. import consts
from .accounts.records import Record
from . import images, posts
from pymongo import MongoClient
from bson.objectid import ObjectId
from jinja2 import Template
from jinja2.filters import do_striptags as striptags
from string import ascii_uppercase, ascii_lowercase
import threading

client = MongoClient()
_db, _collection = consts.MONGO['notifications']
not_collection = client[_db][_collection]

_types = [
    'mention',
    'image_reply',
    'post_reply',
    'image_share',
    'post_share',
    'friend',
    'follower'
]

# Order is stable, this approach is safe
NTYPES = enum.IntEnum('NOTIFICATION_TYPES', _types)

_mtrans = str.maketrans({u: '_' + l for u, l in 
                         zip(ascii_uppercase, ascii_lowercase)})

def _lower_under(clsname):
    return clsname.translate(_mtrans).lstrip('_')

class Notification(abc.Item):

    ''' This class is different from Post and Image in both purpose
        and implementation. '''

    def __init__(self, notification=None):
        self._fields = {}
        self.params = {}
        if notification:
            notification = ObjectId(notification)
            data = not_collection.find_one({self.pk: notification}) or {}
            self._init_setfields(self, data)

    def _prepare(self):
        if self.owner and not isinstance(self.owner, Record):
            self._setfields(self, {'owner': Record(id=self.owner)})

        if self._type_map:
            for field, init in self._type_map.items():
                self.params[field] = init(getattr(self, field))

    def get_html(self, tpl):
        if not isinstance(tpl, Template):
            raise TypeError('Expected {!r}, got {!r}'.format(Template, type(tpl)))
        macro = getattr(tpl.module, _lower_under(type(self).__name__))
        params = {a: self.params[a] for a in macro.arguments if a in self._type_map}
        return macro(**params)

    def get_text(self, tpl=None):
        if not tpl:
            return ''
        return striptags(self.get_html(tpl))

    @classmethod
    def new(cls, acct, **ka):
        if not isinstance(acct, Record):
            raise TypeError
        doc = {'owner': acct.id}
        if getattr(cls, '_ntype', None) is not None:
            doc['type'] = cls._ntype
        doc.update(ka)
        for field, value in ka.items():
            if isinstance(value, abc.Pkeyed):
                doc[field] = value.id
        not_collection.insert_one(doc)
        return cls.fromdata(doc)

    @classmethod
    def delete_unread(cls, acct):
        if not isinstance(acct, Record):
            raise TypeError
        filt = {'owner': acct.id}
        if getattr(cls, '_ntype', None) is not None:
            filt['type'] = cls._ntype
        not_collection.delete_many(filt)
        
    @classmethod
    def delete(cls, acct, ids):
        if not isinstance(acct, Record):
            raise TypeError
        if not ids:
            raise ValueError('Nothing to delete')

        ins = cls.instances(ids)
        # Make a list excluding not `acct`'s images
        valid = [x for x in ins if x.owner == acct]
        filt = {'owner': acct.id, cls.pk: {'$in': [x.id for x in valid]}}
        if getattr(cls, '_ntype', None) is not None:
            filt['type'] = cls._ntype
        not_collection.delete_many(filt)

    def __repr__(self):
        return ''


class MentionNotification(Notification):
    _type_map = {
        'other': lambda x: Record(id=x),
        'post': posts.Post
    }
    _ntype = NTYPES.mention


class ReplyPostNotification(Notification):
    _type_map = {
        'other': lambda x: Record(id=x),
        'post': posts.Post
    }
    _ntype = NTYPES.post_reply


class ReplyImageNotification(Notification):
    _type_map = {
        'other': lambda x: Record(id=x),
        'image': images.Image
    }
    _ntype = NTYPES.image_reply


class SharedPostNotification(Notification):
    _type_map = {
        'other': lambda x: Record(id=x),
        'post': posts.Post
    }
    _ntype = NTYPES.post_share
    
class SharedImageNotification(Notification):
    _type_map = {
        'other': lambda x: Record(id=x),
        'image': images.Image
    }
    _ntype = NTYPES.image_share


class FriendNotification(Notification):
    _type_map = {
        'other': lambda x: Record(id=x),
    }
    _ntype = NTYPES.friend


class FollowerNotification(Notification):
    _type_map = {
        'other': lambda x: Record(id=x),
    }
    _ntype = NTYPES.follower


_ntypes_map = {x._ntype: x for x in Notification.__subclasses__()}


def load(acct, ntype=None, only_unread=True):
    if not isinstance(acct, Record):
        raise TypeError

    if only_unread:
        filt= {'owner': acct.id}
        if ntype is not None:
            filt['type'] = ntype
        it = not_collection.find(filt)
        yield from (_ntypes_map[x['type']].fromdata(x) for x in it)
    else:
        # TODO
        return


def emit_item(item, tpl, types=None):
    if not isinstance(item, (posts.Post, images.Image)):
        raise TypeError

    if types is None:
        types = iter(_ntypes_map.values())

    for t in types:
        if not isinstance(item, posts.Post):
            continue # We don't have notifications about other types yet

        if item.content and t is MentionNotification:
            gen = (Record(name=x) for x in utils.mentions(item.content))
            for acct in gen:
                t.new(acct, post=item, other=item.owner)
                
        elif item.base:
            _shared = {SharedImageNotification, SharedPostNotification}
            _replied = {ReplyImageNotification, ReplyPostNotification}
            if t not in _shared | _replied:
                continue

            base = list(posts.parents(item))[-2]

            if t is SharedPostNotification and isinstance(base, posts.Post):
                t.new(base.owner, post=base, other=item.owner)
            elif t is SharedImageNotification and isinstance(base, images.Image):
                t.new(base.owner, image=base, other=item.owner)
            elif t is ReplyPostNotification and isinstance(base, posts.Post):
                t.new(base.owner, post=base, other=item.owner)
            elif t is ReplyImageNotification and isinstance(base, images.Image):
                t.new(base.owner, image=base, other=item.owner)

            # # TODO: Notification params?
            # args = ({'action': 'notification', 'notification': str(obj), 'ids': ids},)
            # threading.Thread(target=wsinter.async_send, args=args, daemon=True).start()


def emit_relations():
    pass