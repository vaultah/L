import pytest
from app.el.accounts import records
import uuid
from operator import attrgetter


def test_context_updating():
    rec = records.Record.new()
    old = rec.as_dict()
    new = {'name': uuid.uuid4().hex, 'real_name': 'New Real name'}
    inc = {'followers': 1, 'posts': -1, 'images': 10}
        
    # The context manager must be reentrant
    with rec:
        rec.images += inc['images']
        with rec:
            # Some counters
            rec.followers += inc['followers']
            rec.posts += inc['posts']
            # Updates
            rec.real_name = new['real_name']
            rec.name = new['name']

    # Object attributes must be set
    for attr in old.keys() & new.keys():
        assert getattr(rec, attr) == new[attr], attr

    for attr in old.keys() & inc.keys():
        assert getattr(rec, attr) == old[attr] + inc[attr], attr

    # Reload the record
    reloaded = records.Record(id=rec.id)

    # Check if the information has been updated
    assert reloaded == rec
    for attr in ('real_name', 'name', 'followers', 'posts', 'images'):
        assert getattr(reloaded, attr) == getattr(rec, attr), attr

    # Test field removal
    with reloaded:
        reloaded.real_name = None
        reloaded.posts = None

    # Reload again and check their absence
    reloaded = records.Record(id=reloaded.id)
    assert 'real_name' not in reloaded.as_dict()
    assert reloaded.real_name is None
    assert 'posts' in reloaded.as_dict()
    assert reloaded.posts == 0

    # pwd is not a public field
    assert 'pwd' not in reloaded.as_public_dict()


def test_accounts_loading():
    # No `start` and default limit
    accts = [records.Record.new() for _ in range(2)]
    res = list(records.number())
    assert all(isinstance(x, records.Record) for x in res)
    assert len(res) >= len(accts)
    # `start` and default limit
    res = list(records.number(start=min(accts, key=attrgetter('id'))))
    assert all(isinstance(x, records.Record) for x in res)
    assert len(res) >= len(accts)
    # There's no point to test `limit` param specifically


def test_count():
    old = records.total()
    # Dummy account
    records.Record.new()
    assert records.total() - old == 1
