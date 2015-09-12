import abc
import collections

''' We use abstract classes rarely, but this is the place for them '''

class Pkeyed:

    pk = '_id'
    
    @property    
    def id(self):
        return getattr(self, self.pk)


class Item(Pkeyed, metaclass=abc.ABCMeta):
    ''' Abstract class for all content specific classes (e.g.
        `posts.Post` and `images.Image`). They share the same ideas, so 
        it'd be logical for them to inherit one class. '''

    @classmethod
    @abc.abstractmethod
    def delete(cls, account, *args):
        ''' Total number of args depends on the object type '''
        pass

    @classmethod
    @abc.abstractmethod
    def new(cls):
        ''' Create a new object and return created instance(s) '''
        pass
        
    def __repr__(self):
        pass

    def __hash__(self):
        return hash((type(self), self.id))

    @abc.abstractmethod
    def _prepare(self):
        pass

    # Next methods are not abstract
        
    @staticmethod
    def _setfields(instance, data):
        try:
            instance._fields.update(**data)
        except TypeError:
            msg = 'expected a mapping, got {.__class__.__name__}'.format(data)
            raise TypeError(msg) from None
        else:
            return instance

    @classmethod
    def instances(cls, it):
        seq = tuple(it)
        if isinstance(seq[0], dict): # Documents
            yield from (cls.fromdata(x) for x in seq)
        elif isinstance(seq[0], cls): # Ready to go
            yield from seq
        else: # ObjectIds or public ids
            yield from (cls(x) for x in seq)

    @classmethod
    def _init_setfields(cls, instance, data):
        ''' Proxy data to _setfields, but set _exist appropriately'''
        # if data is empty, `instance._exists` must be False
        # if data is not empty, `instance._exists` will be True only if
        # len(data) > 1 (because of the primary field, which can (and will) vary)
        instance._exists = len(data) > 1
        cls._setfields(instance, data)
        instance._prepare()
        return instance

    def add(self, data):
        ''' Add more data to the `self` from `data` and return resulting 
            instance '''
        return self._setfields(self, data)

    @classmethod
    def fromdata(cls, data, **ka):
        ''' Construct the class instance from `data` '''
        return cls._init_setfields(cls(**ka), data)

    def good(self):
        ''' Check if the current instance refers to a valid and
            existing object '''
        return self._exists

    def __getattr__(self, attr):
        return self._fields.get(attr)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError('Can\'t compare instances of '
                                      '{!r} and {!r}'.format(type(self), type(other)))
        else:
            return self.id == other.id

    def as_dict(self):
        rv = collections.defaultdict(lambda: None)
        rv.update(self._fields)
        if self.pk != 'id':
            rv['id'] = rv.pop(self.pk)
        return rv

    def as_public_dict(self):
        # Same as `as_dict` but hides the sensitive fields and converts 'id'
        # to string
        rv = self.as_dict()
        rv['id'] = str(rv['id'])
        for field in (self.private or ()):
            rv.pop(field)
        return rv



class Scorable(Pkeyed):

    ''' This class works in assumption that there can be only one updatable
        attribute and we can update the database easily (instantly).

        To achieve this we have overriden __setattr__ in Record, because there
        were at least 10 updatable attrs there.  

        Oh yeah, and this class is not abstract '''

    @property
    def score(self):
        # Perfectly ok
        return self._fields.get('score', 0)

    @score.setter
    def score(self, value):
        # Unified interface ftw
        self.collection.update_one({self.pk: self.id},
                                   {'$inc': {'score': value - self.score}})
        self._setfields(self, {'score': value})
