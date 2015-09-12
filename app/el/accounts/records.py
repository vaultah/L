from ... import consts
from ..misc import abc, utils
import collections
from bson.objectid import ObjectId
from pymongo import MongoClient

client = MongoClient()


class Record(abc.Item):
    ''' Represents a single account.
        Arguments have the same name as corresponding fields in the
        database. Submitted value must uniquely identify the account. 

        Use the instance as a context manager, if you want to update
        the document 

        This CM is reentrant '''
        
    _db, _collection = consts.MONGO['records']  
    collection = client[_db][_collection]
    private = frozenset(('pwd',))
    restricted = frozenset(('_updates', '_removals', '_fields', 
                            '_counters', '__context_depth__'))
    _counters_fields = frozenset(('followers', 'posts', 'following', 
                                  'friends', 'images'))

    def __init__(self, **ka):
        # Set it first, otherwise you'll get a recursion
        self.__context_depth__ = 0
        # Preset some defaults
        self._fields = dict.fromkeys(self._counters_fields, 0)
        if ka:
            # Will search by one pair
            f, v = ka.copy().popitem()
            if f == 'id':
                f = self.pk
                v = ObjectId(v)
            self._init_setfields(self, self.collection.find_one({f: v}) or {})

    def _prepare(self):
        pass

    def __setattr__(self, name, val):
        # FIXME I'm ugly
        if name not in self.restricted and self.__context_depth__:
            if val is not None:
                if name in self._counters_fields:
                    self._counters[name] += val - self._fields[name]
                else:
                    self._updates[name] = val
                self._setfields(self, {name: val})
            else:
                self._removals.append(name)
                if name in self._fields:
                    self._fields.pop(name)
        else:
            super().__setattr__(name, val)

    def delete(self):
        # FIXME: Put everything we need to completely remove this account
        # FIXME: here
        # if not self.good():
        #     raise ValueError('Attempting to delete non-existant record')
        pass

    def __repr__(self):
        return ('<Record object at {0:#x}: {1.pk}={1.id}, '
                'name={1.name!r}>').format(id(self), self)

    def __enter__(self):
        ''' Return the instance.
            A caller can update the fields, the updated document will be put 
            into database on __exit__() '''
        self._updates = self._updates or {}
        self._removals = self._removals or []
        self._counters = self._counters or collections.Counter()
        # Must be set at the end of this method
        self.__context_depth__ += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Must be set at the beginning of this method
        self.__context_depth__ -= 1
        if not self.__context_depth__:
            ops = {'$inc': self._counters, '$set': self._updates,
                   '$unset': dict.fromkeys(self._removals)}
            # Filter empty values out
            ops = {k: v for k, v in ops.items() if v}
            if ops:
                self.collection.update_one({self.pk: self.id}, ops)
            # Restore to the initial state
            self._counters.clear()
            self._updates.clear()
            self._removals[:] = []

        # document goes into db no matter what, ignore exceptions (?)

    @classmethod
    def new(cls, name, hashed):
        data = {'name': name, 'pwd': hashed}
        res = cls.collection.update_one({'name': name}, {'$setOnInsert': data},
                                        upsert=True)
        # XXX: Raise UserExists or something
        if res.upserted_id is None:
            raise ValueError
        else:
            data[cls.pk] = res.upserted_id
        return cls.fromdata(data)


def number(number=50, start=None):
    if isinstance(start, ObjectId):
        data = Record.collection.find({Record.pk: {'$lt': start}})
    else:
        data = Record.collection.find()
    it = data.sort([('$natural', -1)]).limit(number)
    yield from map(Record.fromdata, it)


def total():
    return Record.collection.count()