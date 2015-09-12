import pytest
from app.el.accounts import profile
from app.el.accounts.records import Record

def test_profile():
    acct = Record.new()
    res = profile.profile(acct, minimal=False)
    assert 'avatar' in res
    assert 'website_link' in res
    assert 'country_name' in res
    res = profile.profile(acct)
    assert 'avatar' in res
    assert 'website_link' not in res
    assert 'country_name' not in res
