import pytest
from app.el import notifications as no
from app.el.accounts.records import Record

types = ('MentionNotification', 'ReplyPostNotification', 'ReplyImageNotification',
         'SharedPostNotification', 'SharedImageNotification', 'FriendNotification',
         'FollowerNotification')

@pytest.mark.parametrize('nt', types, ids=types)
def test_notifications(nt):
    this, other = Record.new(), Record.new()
    klass = getattr(no, nt)
    o = klass.new(this, other=other)
    assert o.good()
    assert o.id
    assert list(no.load(this))
    no.Notification.delete(this, [o.id])
    assert not list(no.load(this))