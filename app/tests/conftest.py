import pytest
import sys
import functools
import collections.abc
from collections import ChainMap
from inspect import signature
from pathlib import Path
from uuid import uuid4
from http import cookiejar
from unittest.mock import patch
from itertools import cycle, chain, count

from app.el.misc import storage
from app.el.accounts import auth
from app.el.accounts.records import Record
from app.el.images import Image
from app.el.posts import Post

tests_dir = Path(__file__).parent


class Memorize(collections.abc.Iterator):

    def __init__(self, it):
        self.it = it
        self.values = []

    def __iter__(self):
        return self

    def __next__(self):
        nxt = next(self.it)
        self.values.append(nxt)
        return nxt

    def __repr__(self):
        return '<{.__class__.__name__}: {!r} produced {!r} values>'.format(
                                                self, self.it, len(self.values))


def pytest_addoption(parser):
    parser.addoption('--no-send', action='store_true', default=False,
                     help='Don\'t send mail during the tests') 
    parser.addoption('--no-urls', action='store_true', default=False,
                     help='Do not test downloading from urls')
    parser.addoption('--send-to', action='store', help='Send mail to this address',
                     default='flwaultah@gmail.com') 


@pytest.fixture(autouse=True)
def flushdb():
    for name, ob in vars(storage).items():
        if callable(ob) and 'get_' in name and '_connection' in name:
            ob().flushdb()


def _close_all(files):
    ''' Close all file(-like) objects from `files` '''
    for x in files:
        x.close()


def _opened_images(suf=None):
    p = sorted(Path(tests_dir / 'images').iterdir())
    it = (x.open('rb') for x in cycle(p) if suf is None or x.suffix == suf)
    yield from it


''' These functions are not really fixtures by definition. They can't 
    "reliably" execute. 

    The downside of using patched methods is that
    we'll need to specify default valuess explicitly ;_; '''


@pytest.yield_fixture(scope='session', 
                      params=['.gif', '.png', '.jpg'],
                      ids=['GIF images', 'PNG images', 'JPG images'])
def image_files(request):
    memo = Memorize(_opened_images(request.param))
    yield memo
    request.addfinalizer(functools.partial(_close_all, memo.values))


@pytest.yield_fixture(autouse=True, scope='session')
def patch_new_record():
    def _decorate(func):
        def wrapper(*a, **ka):
            args = signature(func).bind_partial(*a, **ka).arguments
            plaintext = None
            if 'name' not in args:
                args['name'] = uuid4().hex
            if 'pwd' not in args:
                plaintext = uuid4().hex
                # We need to run tests faster.
                # This doesn't get called for authentication tests.
                with patch.object(auth, 'BCRYPT_ROUNDS', 4):
                    args['pwd'] = auth.hashed(plaintext)
            rec = func(**args)
            acid = auth.ACID.new(id=auth._gen_acid())
            token = acid.add_token(rec, session=True)
            rec.plaintext_pwd = plaintext
            rec.cookies = {'acid': acid, 'token': token}
            return rec
        return wrapper

    with patch.object(Record, 'new', _decorate(Record.new)):
        yield Record


@pytest.yield_fixture(autouse=True, scope='session')
def patch_new_post(patch_new_record):
    def _decorate(func):
        def wrapper(*a, **ka):
            args = signature(func).bind_partial(*a, **ka).arguments
            if 'poster' not in args:
                args['poster'] = Record.new()
            if 'content' not in args:
                args['content'] = '<string>'
            return func(**args)
        return wrapper

    with patch.object(Post, 'new', _decorate(Post.new)):
        yield Post


@pytest.yield_fixture(autouse=True, scope='session')
def patch_new_image(request, patch_new_record):
    opened = Memorize(_opened_images('.jpg'))
    def _decorate(func):
        def wrapper(*a, **ka):
            args = signature(func).bind_partial(*a, **ka).arguments
            if 'acct' not in args:
                args['acct'] = Record.new()
            if 'images' not in args:
                args['images'] = [next(opened)]
            return func(**args)
        return wrapper

    with patch.object(Image, 'new', _decorate(Image.new)):
        yield Image

    request.addfinalizer(functools.partial(_close_all, opened.values))