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
from itertools import groupby, chain
import base64
from collections import namedtuple
from fused import fields

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
    return Record.new(name=name, pwd=hashed(pwd))        


class ResetKey(abc.Item):

    account = fields.Foreign('Record', required=True)
    time = fields.Field(required=True) # TODO: fused float

    def __init__(self, *a, **ka):
        super().__init__(*a, **ka)
        if self.good() and float(self.time) < time.time() - reset_key_age:
            self.delete()

    def send(self, **ka):
        # FIXME: Handle exceptions
        if not isinstance(ka.get('template'), jinja2.Template):
            raise TypeError('Expected jinja2.Temlate')

        contents = ["We've received a request to reset your password, so here we are. "
                    "The link below is active for 6 hours.",
                    "Email was sent to {}.".format(self.account.email)]

        html = ka['template'].render(contents=contents, host=ka['host'],
                                     reset_link=self.id, name=self.account.name)
        msg = MIMEText(html, 'html')
        msg['Subject'] = 'Password reset'
        msg['From'] = 'accounts@{}'.format(consts.ext.SMTP_HOST)
        msg['To'] = self.account.email
        smtp = smtplib.SMTP(consts.ext.SMTP_HOST)
        smtp.send_message(msg)
        smtp.quit()

    @classmethod
    def new_from_unique(cls, name=None, email=None, account=None, **ka):
        if account is not None:
            ka['account'] = account
        elif name is not None:
            ka['account'] = Record(name=name)
        elif email is not None:
            ka['account'] = Record(email=email)
        else:
            raise ValueError
        return cls.new(**ka)

    @classmethod
    def new(cls, **ka):
        if 'id' not in ka:
            ka['id'] = utils.unique_hash()

        if 'time' not in ka:
            ka['time'] = time.time()

        return super().new(**ka)


TokenTuple = namedtuple('TokenTuple', ['token', 'record', 'ttl', 'is_session'])


class ACID(abc.Item):
    # Store cookies and sessions in separate Sorted Sets
    cookies = fields.SortedSet(standalone=True)
    sessions = fields.SortedSet(standalone=True)
    # Map tokens to accounts
    tokens = fields.Hash(standalone=True)

    def add_token(self, acct, token=None, session=False, score=None):
        if not isinstance(acct, Record):
            raise TypeError

        if score is None:
            score = time.time()

        if token is None:
            token = _gen_token()

        with self:
            (self.sessions if session else self.cookies).zadd(score, token)
            self.tokens.hset(token, acct.id)

        return token

    def delete_tokens(self, *tokens):
        with self:
            self.tokens.hdel(*tokens)
            self.sessions.zrem(*tokens)
            self.cookies.zrem(*tokens)

    def all_tokens(self):
        with self:
            self.cookies.zrange(0, -1, withscores=True)
            self.sessions.zrange(0, -1, withscores=True)
            self.tokens.hgetall()
            cookies, sessions, map = self.redis.execute()

        for token, timestamp in cookies:
            ttl = timestamp - time.time() + cookie_age
            yield TokenTuple(self.decode(fields.String, token),
                             Record(id=map[token]), ttl, False)

        for token, timestamp in sessions:
            ttl = timestamp - time.time() + session_age
            yield TokenTuple(self.decode(fields.String, token),
                             Record(id=map[token]), ttl, True)


class Current:


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
        
        acid = ACID(id=acid)
        if not acid.good():
            return False

        tokens = set(acid.all_tokens())
        if not tokens:
            return False

        uptodate = set()

        for t in tokens:
            if t.ttl > 0:
                uptodate.add(t)
                self.records[t.record] = t
                self.tokens[t.token] = t

        # No tokens left, delete the ACID
        if not uptodate:
            acid.delete()
            return False
        elif len(uptodate) < len(tokens):
            # Delete the outdated tokens
            acid.delete_tokens(*tokens - uptodate)
        
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