from ... import consts
from ..misc import abc, utils
import collections

class Record(abc.Item):

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