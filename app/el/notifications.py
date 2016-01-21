import enum
import warnings
from collections import ChainMap
from .misc import utils, abc
from .. import consts
from .accounts.records import Record
from . import images, posts
from jinja2 import Template
from jinja2.filters import do_striptags as striptags
from string import ascii_uppercase, ascii_lowercase
import threading
from fused import fields

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
        if getattr(cls, 'type', None) is not None:
            doc['type'] = cls.type
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
        if getattr(cls, 'type', None) is not None:
            filt['type'] = cls.type
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
        if getattr(cls, 'type', None) is not None:
            filt['type'] = cls.type
        not_collection.delete_many(filt)


class MentionNotification(Notification):
    other = fields.Foreign(Record)
    post = fields.Foreign(posts.Post)
    type = NTYPES.mention


class ReplyPostNotification(Notification):
    other = fields.Foreign(Record)
    post = fields.Foreign(posts.Post)
    type = NTYPES.post_reply


class ReplyImageNotification(Notification):
    other = fields.Foreign(Record)
    image = fields.Foreign(images.Image)
    type = NTYPES.image_reply


class SharedPostNotification(Notification):
    other = fields.Foreign(Record)
    post = fields.Foreign(posts.Post)
    type = NTYPES.post_share
    
class SharedImageNotification(Notification):
    other = fields.Foreign(Record)
    image = fields.Foreign(images.Image)
    type = NTYPES.image_share


class FriendNotification(Notification):
    other = fields.Foreign(Record)
    type = NTYPES.friend


class FollowerNotification(Notification):
    other = fields.Foreign(Record)
    type = NTYPES.follower


types_map = {x.type: x for x in Notification.__subclasses__()}


def load(acct, ntype=None, only_unread=True):
    if not isinstance(acct, Record):
        raise TypeError

    if only_unread:
        filt= {'owner': acct.id}
        if ntype is not None:
            filt['type'] = ntype
        it = not_collection.find(filt)
        yield from (types_map[x['type']].fromdata(x) for x in it)
    else:
        # TODO
        return


def emit_item(item, tpl, types=None):
    if not isinstance(item, (posts.Post, images.Image)):
        raise TypeError

    if types is None:
        types = iter(types_map.values())

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

            base = list(posts.ancestors(item))[-2]

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
            # threading.Thread(target=ws.async_send, args=args, daemon=True).start()


def emit_relations():
    pass