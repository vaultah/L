from .records import Record
from ... import consts
from bson.objectid import ObjectId
from pymongo.cursor import CursorType
from pymongo import MongoClient

client = MongoClient()

_db, _collection = consts.MONGO['followers']
followers_collection = client[_db][_collection]
_db, _collection = consts.MONGO['blocked']
block_collection = client[_db][_collection]

# 'req' = 'requester'
# 'sub' = 'subject'

# FOLLOWERS

def follow(req, sub):
    if not (isinstance(req, Record) and isinstance(sub, Record)):
        raise TypeError
    followers_collection.insert_one({'req': req.id, 'sub': sub.id})
    with sub as record:
        record.followers += 1


def unfollow(req, sub):
    if not (isinstance(req, Record) and isinstance(sub, Record)):
        raise TypeError
    followers_collection.delete_one({'req': req.id, 'sub': sub.id})
    with sub as record:
        record.followers -= 1


def is_follower(req, sub):
    if not (isinstance(req, Record) and isinstance(sub, Record)):
        raise TypeError
    match = followers_collection.find_one({'req': req.id, 'sub': sub.id})
    return match is not None


def are_friends(*a):
    if not all(isinstance(x, Record) for x in a):
        raise TypeError
    if len(a) != 2:
        raise ValueError('Exactly 2 arguments are required')
    filt = {'$or': [{'req': x.id, 'sub': y.id} for x, y in zip(a, a[::-1])]}
    return followers_collection.find(filt).count() == 2


# BLOCKING

def is_blocked(req, sub):

    if not (isinstance(req, Record) and isinstance(sub, Record)):
        raise TypeError
    res = block_collection.find_one({'req': req.id, 'sub': sub.id})
    return res is not None


def block(req, sub):
    if not (isinstance(req, Record) and isinstance(sub, Record)):
        raise TypeError
    res = block_collection.insert_one({'req': req.id, 'sub': sub.id})
    return res.inserted_id is not None


def unblock(req, sub):
    if not (isinstance(req, Record) and isinstance(sub, Record)):
        raise TypeError
    res = block_collection.delete_one({'req': req.id, 'sub': sub.id})
    return res.deleted_count == 1

# FEED
    
def feedgetters(acct):
    ''' Get the tuple of ids of all friends and followers of `acct` '''
    if not isinstance(acct, Record):
        raise TypeError
    cur = followers_collection.find({'sub': acct.id},
                                    cursor_type=CursorType.EXHAUST,
                                    projection={'_id': False, 'sub': False})
    return tuple(x['req'] for x in cur)
