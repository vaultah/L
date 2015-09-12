import pytest
from app.el import ratings
from app.el.accounts.records import Record
from app.el.posts import Post
from app.el.images import Image


@pytest.mark.parametrize('item_type',
    [Image, Post],
    ids=['image', 'post']
)
def test_all(item_type):
    item = item_type.new()
    # Won't fail for Image
    try:
        item = next(item)
    except TypeError:
        pass

    account = Record.new()

    old_score = item.score
    ratings.up(account, item)
    assert item.score == old_score + 1
    # No permission checking
    ratings.down(account, item)
    assert item.score == old_score - 1
    ratings.un(account, item)
    assert item.score == old_score
