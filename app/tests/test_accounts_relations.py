import pytest
from app.el.accounts import relations
from app.el.accounts.records import Record


def test_followers_and_friends():
    this, other = (Record.new() for _ in range(2))

    relations.follow(other, this)
    assert relations.is_follower(other, this)
    assert not relations.are_friends(other, this)

    relations.follow(this, other)
    assert relations.is_follower(this, other)
    assert relations.are_friends(other, this)

    relations.unfollow(this, other)
    assert not relations.is_follower(this, other)
    assert not relations.are_friends(other, this)


def test_feedgetters():
    this, *other = (Record.new() for _ in range(3))
    for x in other:
        relations.follow(x, this)
    
    it = relations.feedgetters(this)
    assert sum(1 for _ in it) == len(other)


def test_blocked():
    this, other = (Record.new() for _ in range(2))
    assert not relations.is_blocked(this, other)
    relations.block(this, other)
    assert relations.is_blocked(this, other)
    relations.unblock(this, other)
    assert not relations.is_blocked(this, other)
