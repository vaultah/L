import pytest
from app.el.accounts import records
import uuid
from operator import attrgetter


def test_context_updating():
    rec = records.Record.new()
    old = rec.as_dict()
    new = {'name': uuid.uuid4().hex, 'real_name': 'New Real name'}

    assert rec.images.zcard() == 0
    assert rec.posts.zcard() == 0

    # The context manager must be reentrant.
    # add_<something> usually operate on real primary keys,
    # but we don't have to use real primary keys here
    with rec:
        rec.name = new['name']
        rec.add_image('A')
        with rec:
            rec.add_post('B')
            rec.add_post('C')
            rec.real_name = new['real_name']

    # Object attributes must be set
    for attr in old.keys() & new.keys():
        assert getattr(rec, attr) == new[attr], attr

    assert rec.images.zcard() == 1
    assert rec.posts.zcard() == 2

    # Reload the record
    reloaded = records.Record(id=rec.id)

    # Check if the information has been updated
    assert reloaded == rec
    for attr in ('real_name', 'name'):
        assert getattr(reloaded, attr) == getattr(rec, attr), attr

    assert reloaded.images.zcard() == 1
    assert reloaded.posts.zcard() == 2

    # Test field removal
    with reloaded:
        del reloaded.real_name
        del reloaded.posts

    assert reloaded.real_name is None
    # Reload again and check their absence
    reloaded = records.Record(id=reloaded.id)
    assert 'real_name' not in reloaded.as_dict()
    assert reloaded.real_name is None
    assert reloaded.posts.zcard() == 0

    # TODO:
    # # pwd is not a public field
    # assert 'pwd' not in reloaded.as_public_dict()


def test_compound():
    rec = records.Record.new()
    singular = ('image', 'post', 'follower', 'following',
                'friend', 'notification')
    plural = ('images', 'posts', 'followers', 'following',
              'friends', 'notifications')

    for x in singular:
        getattr(rec, 'add_' + x)('A')

    for x in plural:
        res = list(getattr(rec, 'get_' + x)())
        assert len(res) == 1, res
        assert res == ['A'], res

    for x in singular:
        getattr(rec, 'delete_' + x)('A')

    for x in plural:
        res = list(getattr(rec, 'get_' + x)())
        assert not res, res
        assert res == [], res
