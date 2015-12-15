import pytest
import string
from app.el.accounts import auth
from app.el.accounts.records import Record
from app.el.misc import utils
from app import consts
import time
import uuid
from jinja2 import Template
from pathlib import Path


def time_machine(forward):
    def wrapper(f):
        def _wrapper():
            return f() + forward + 100
        return _wrapper
    return wrapper


cookie_time = time_machine(auth.cookie_age)(time.time)
session_time = time_machine(auth.session_age)(time.time)


@pytest.mark.slow
def test_signup():
    rec = auth.signup(uuid.uuid4().hex, '<string>')
    assert isinstance(rec, Record)
    assert rec.good()


def test_signin():
    acct = Record.new()
    assert not auth.signin(acct, 'guaranteed to be incorrect')
    assert auth.signin(acct, acct.plaintext_pwd)


_malformed_passwords = {
    string.whitespace: 'whitespace',
    'conтрaseña': "non ASCII",
    '\x00a': 'NUL byte and a char' # because bcrypt
}
@pytest.mark.slow
@pytest.mark.parametrize('pwd',
    list(_malformed_passwords.keys()),
    ids=list(_malformed_passwords.values())
)
def test_hashing(pwd):
    hashed = auth.hashed(pwd)
    assert auth.compare(pwd, hashed)
    assert hashed != auth.hashed('')


def test_cookies():
    account = Record.new()
    # No distinction between real cookies and session
    acid, *tokens = (utils.unique_hash() for _ in range(3))
    for token in tokens:
        auth.cookies.save(acct=account, acid=acid, token=token)

    it = auth.cookies.get_by_acid(acid)
    assert sum(1 for _ in it) == len(tokens)
    auth.cookies.delete_tokens(tokens)
    assert next(auth.cookies.get_by_acid(acid), None) is None


def test_current(monkeypatch):
    account = Record.new()
    acid, *tokens = (utils.unique_hash() for _ in range(3))
    # Split the list (aproximatly) in half and save the tokens
    cookies, sessions = [tokens[0]], [tokens[-1]]

    for x in cookies:
        auth.cookies.save(acct=account, acid=acid, token=x)

    for x in sessions:
        auth.cookies.save(acct=account, acid=acid, token=x, session=True)

    # Test the attributes and the return value
    for token in tokens:
        current = auth.Current(token=token, acid=acid)
        assert current.loggedin
        assert not current.multi
        assert current.record == account

    # TODO: Be consistent and use `patch` from `unittest.mock`?
    # Test session lifetime
    monkeypatch.setattr('time.time', session_time)
    for token in sessions:
        current = auth.Current(token=token, acid=acid)
        assert not current.loggedin
        assert not current.multi

    # Test cookie lifetime
    monkeypatch.setattr('time.time', cookie_time)
    for token in cookies:
        current = auth.Current(token=token, acid=acid)
        assert not current.loggedin
        assert not current.multi


def test_multilogin(monkeypatch):
    # TODO: Test switch_to
    acct1, acct2 = Record.new(), Record.new()
    ids = {acct1.id, acct2.id}
    acid, token1, token2 = (utils.unique_hash() for _ in range(3))

    # Save the first token
    auth.cookies.save(acct=acct1, token=token1, acid=acid)
    # Save the second token (with different lifetime)
    auth.cookies.save(acct=acct2, token=token2, acid=acid, session=True)

    # Both tokens must work correctly
    current = auth.Current(token=token1, acid=acid)
    assert current.loggedin
    assert current.record == acct1
    assert current.multi
    assert {x.id for x in current.records} == ids

    current = auth.Current(token=token2, acid=acid)
    assert current.loggedin
    assert current.record == acct2
    assert current.multi
    assert {x.id for x in current.records} == ids

    # Test tokens' lifetime
    monkeypatch.setattr('time.time', session_time)
    current = auth.Current(token=token2, acid=acid)
    assert not current.loggedin
    assert not current.multi

    monkeypatch.setattr('time.time', cookie_time)
    current = auth.Current(token=token1, acid=acid)
    assert not current.loggedin
    assert not current.multi


def test_reset():
    account = Record.new()
    with account:
        # Set the one we can actually check
        account.email = pytest.config.getoption('--send-to')

    for reset in ({'name': account.name}, {'email': account.email}, {'acct': account}):
        inst = auth.ResetNoKey(**reset)
        assert inst.good()
        
        if pytest.config.getoption('--no-send'):
            # set .key anyway
            inst._generate_key()
        else:
            with (consts.VIEWS / 'email' / 'password-reset.html').open() as tf:
                # No need to load environment
                inst.send(host='not_critical', template=Template(tf.read()))

        assert auth.Reset(inst.key).good()
        # Must not be able to reuse
        assert not auth.Reset(inst.key).good()

