from .accounts import relations
from .accounts.records import Record
from .images import Image
from .posts import Post
from .misc import abc
from .. import consts
from pymongo import MongoClient

client = MongoClient()
_db, _collection = consts.MONGO['ratings']
ratings_collection = client[_db][_collection]


def _rated(acct, item):
    ''' Return the vote information (or None if no such vote was given) '''
    data = ratings_collection.find_one({'rater': acct.id, 'item': item.id})
    return data


def _remove_vote(acct, item):
    ratings_collection.delete_one({'rater': acct.id, 'item': item.id})


def _save_vote(acct, item, value):
    ratings_collection.insert_one({'rater': acct.id, 'item': item.id, 'value': value})


def _update_vote(acct, item, new):
    ''' Change the vote (well, not exatly "change") '''
    _remove_vote(acct, item)
    _save_vote(acct, item, new)


def up(acct, item):
    if not isinstance(item, abc.Scorable):
        raise TypeError('We expect subclasses of "Scorable" here')

    if not isinstance(acct, Record):
        raise TypeError('We expect instances of "Record"')

    data = _rated(acct, item)

    if not data:
        _save_vote(acct, item, 1)
        item.score += 1
    elif data['value'] == -1:
        _update_vote(acct, item, 1)
        item.score += 2



def down(acct, item):
    if not isinstance(item, abc.Scorable):
        raise TypeError('We expect subclasses of "Scorable" here')

    if not isinstance(acct, Record):
        raise TypeError('We expect instances of "Record"')

    data = _rated(acct, item)

    if not data:
        _save_vote(acct, item, -1)
        item.score -= 1
    elif data['value'] != -1:
        _update_vote(acct, item, -1)
        item.score -= 2


def un(acct, item):
    if not isinstance(item, abc.Scorable):
        raise TypeError('We expect subclasses of "Scorable" here')

    if not isinstance(acct, Record):
        raise TypeError('We expect instances of "Record"')

    data = _rated(acct, item)

    if data:
        _remove_vote(acct, item)
        item.score -= data['value']