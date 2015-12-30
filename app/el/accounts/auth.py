from email.mime.text import MIMEText
import hashlib
import os
import smtplib
import sys
import time
import datetime
import math
import sha3
import bcrypt
import jinja2
import functools
from operator import attrgetter
from itertools import groupby
import base64
from collections import namedtuple

from ..misc import utils, abc
from ... import consts
from .records import Record

# 2 weeks
cookie_age = 60*60*24*7*2
# 4 hours
session_age = 60*60*4
# 6 hours
reset_key_age = 60*60*6

_gen_token = functools.partial(utils.unique_hash, bits=384)
_gen_acid = functools.partial(utils.unique_hash, bits=384)
_algo = hashlib.sha3_512
BCRYPT_ROUNDS = 16  


def _prehash(pwd):
    dig = _algo(bytes(pwd, 'utf-8')).digest()
    return base64.b64encode(dig)[:72]


def compare(pwd, other):
    return hashed(pwd, other) == other


def hashed(pwd, salt=None):
    if salt is None:
        salt = bcrypt.gensalt(BCRYPT_ROUNDS)
    return bcrypt.hashpw(_prehash(pwd), salt)


def signin(acct, pwd):
    if not isinstance(acct, Record):
        raise TypeError
    return compare(pwd=pwd, other=acct.pwd)


def signup(name, pwd):
    return Record.new(name, hashed(pwd))        


class ResetNoKey:

    ''' Validate provided info and send an email with a key. '''

    def __init__(self, **ka):
        # Just one of the arguments has to be provided
        if len(ka) != 1:
            raise ValueError('Too many arguments')

        self.record = ka.get('acct') or Record(**ka)

    def _send(self, **ka):
        # FIXME: Handle exceptions
        if not isinstance(ka.get('template'), jinja2.Template):
            raise TypeError('Expected jinja2.Temlate')

        contents = ["We've received a request to reset your password, so here we are. "
                    "The link below is active for 6 hours.",
                    "Email was sent to {}.".format(self.record.email)]

        html = ka['template'].render(contents=contents, host=ka['host'],
                                     reset_link=self.key, name=self.record.name)
        msg = MIMEText(html, 'html')
        msg['Subject'] = 'Password reset'
        msg['From'] = 'accounts@{}'.format(consts.ext.SMTP_HOST)
        msg['To'] = self.record.email
        smtp = smtplib.SMTP(consts.ext.SMTP_HOST)
        smtp.send_message(msg)
        smtp.quit()

    def _generate_key(self):
        self.key = utils.unique_hash()
        reset_collection.insert_one({'account': self.record.id, 'key': self.key})

    def good(self):
        return self.record.good()

    def send(self, **ka):
        self._generate_key()
        self._send(**ka)


class Reset:#(abc.Pkeyed):

    ''' Check if key is legit '''

    def __init__(self, key):
        self.key = key
        self._exists = self._check_key()

    def _check_key(self):
        data = reset_collection.find_one({'key': self.key})
        if data:
            gentime = datetime.datetime.timestamp(data[self.pk].generation_time)
            # One-off, literally
            self._delete_key()
            if gentime >= time.time() - reset_key_age:
                return True

        return False

    def _delete_key(self):
        reset_collection.delete_one({'key': self.key})

    def good(self): 
        return self._exists
        

# TODO: Token as `Item`?
class cookies:

    @classmethod
    def save(cls, acid, token, acct, session=False):
        if not isinstance(acct, Record):
            raise TypeError

        cls.collection.insert_one({'account': acct.id, 'token': token,
                                   'acid': acid, 'session': bool(session)})
    @classmethod
    def delete_acid(cls, acid):
        cls.collection.delete_many({'acid': acid})

    @classmethod
    def delete_tokens(cls, tokens):
        cls.collection.delete_many({'token': {'$in': list(tokens)}})

    @classmethod
    def get_by_acid(cls, acid):
        data = cls.collection.find({'acid': acid})
        yield from data.sort([('$natural', 1)])

    @classmethod
    def generate_and_save(cls, **ka):
        if 'acid' not in ka:
            ka['acid'] = _gen_acid()

        if 'token' not in ka:
            ka['token'] = _gen_token()

        cls.save(**ka)
        return ka['acid'], ka['token']


class Current:

    _tup_cls = namedtuple('TokenTuple', ['token', 'record', 'ttl', 'is_session'])

    def __init__(self, acid, token):
        # Set defaults
        self.multi = False
        self.record = None
        self.max_ttl = None
        self.last = None
        self.set_token = False
        self.records = {}
        self.tokens = {}
        # `ka` contains cookie name -> cookie value pairs
        self.loggedin = self._logged(acid, token)

    def _newer_token(self):
        self.set_token = True

    def _logged(self, acid, token):
        if acid is None:
            return False

        rows = list(cookies.get_by_acid(acid))

        if not rows:
            return False

        def _make_ntuple(x):
            # Calculate TTL
            ts = datetime.datetime.timestamp(x['_id'].generation_time)
            is_session = x.get('session', False)
            ttl = ts - time.time() + (session_age if is_session else cookie_age)
            # Load record, construct instance, add instance to dicts
            token, record = x['token'], Record(id=x['account'])
            o = self._tup_cls(token, record, ttl, is_session)
            if o.ttl > 0:
                self.records[record] = o
                self.tokens[token] = o
            return o

        tups = {_make_ntuple(x) for x in rows}
        uptodate = {x for x in tups if x.ttl > 0}

        # No tokens left, delete the ACID
        if not uptodate:
            cookies.delete_acid(acid)
            return False

        # Delete the outdated tokens
        cookies.delete_tokens([x.token for x in tups - uptodate])
        
        # Get max ttl and the corresponsing namedtuple instance
        self.max_ttl, self.last = max((x.ttl, x) for x in uptodate)

        # Current token (can be None)
        if token is not None:
            try:
                self.token = (token, self.tokens[token].ttl)
            except KeyError:
                # Token not in self.tokens
                return False
        else:
            self.token = self.last
            self._newer_token()

        # We need self values outside the BL layer
        self.acid = acid, self.max_ttl
        self.multi = len(self.records) > 1
        self.uptodate = uptodate
        self.record = self.tokens[self.token[0]].record
        return True

    def switch_to(self, acct):
        if not isinstance(acct, Record):
            raise TypeError

        try:
            tup = self.records[acct]
        except KeyError:
            # We can't swtich to account, re-raising the exception
            raise ValueError('Account not in the container') from None
        else:
            self.token = (tup.token, tup.ttl)
            self.record = tup.record
            self._newer_token()