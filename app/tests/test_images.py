import pytest
import webtest
from pathlib import Path
from app.el.images import Image, raw as load_raw
from app.el.accounts.records import Record

files = Path(__file__).parent / 'images'


@pytest.mark.parametrize('file', 
    [files / 'test.jpg', files / 'test.png', files / 'test.gif'],
    ids=['JPG images', 'PNG images', 'GIF images']
)
def test_create(file):
    acct = Record.new()
    with file.open('rb') as file1, file.open('rb') as file2:
        gen = Image.new(acct, [file1, file2],
                        allow_gif=file.suffix == '.gif')
        objects = list(gen)
    assert len(objects)
    # True with allow_gif = True
    assert len(objects) == 2
    assert all(isinstance(x, Image) for x in objects)
    assert all(x.owner == acct for x in objects)
    assert all(x.good() for x in objects)

    if file.suffix == '.gif':
        with file.open('rb') as f:
            objects = list(Image.new(acct, [f], allow_gif=False))
        assert not objects
        assert len(objects) == 0


print(pytest.config.getoption('--no-urls'), pytest.config.getoption, pytest.config, type(pytest.config), pytest)
@pytest.mark.skipif(pytest.config.getoption('--no-urls'), reason='Skipping urls')
@pytest.mark.parametrize('url', 
    ['http://dummyimage.com/600x400/000/fff.gif',
     'http://dummyimage.com/600x400/000/fff.png',
     'http://dummyimage.com/600x400/000/fff.jpg'],
    ids=['GIF image', 'PNG image', 'JPG image']
)
@pytest.mark.slow
def test_downloading(url):
    acct = Record.new()
    # Working links
    downloaded = list(Image.new(acct, [url], allow_gif=True))
    assert len(downloaded)
    assert len(downloaded) == 1
    assert all(isinstance(x, Image) for x in downloaded)
    assert all(x.owner == acct for x in downloaded)
    assert all(x.good() for x in downloaded)


@pytest.mark.skipif(pytest.config.getoption('--no-urls'), reason='Skipping urls')
@pytest.mark.parametrize('url',
    ['http://dummyimage.com', '', 'nonsense'],
    ids=['HTML page', 'Empty string', 'nonsense']
)
@pytest.mark.slow
def test_downloading_bad_urls(url):
    acct = Record.new()
    bad = list(Image.new(acct, [url], allow_gif=True))
    assert not bad # ♬ Not baaaaaad at a-a-a-all ♬


@pytest.mark.parametrize('file', 
    [files / 'test.jpg', files / 'test.png', files / 'test.gif'],
    ids=['JPG images', 'PNG images', 'GIF images']
)
def test_set(file):
    # Test setcover and setavatar methods
    with file.open('rb') as f:
        obj = next(Image.new(Record.new(), [f], allow_gif=file.suffix == '.gif'))
    obj.setavatar()
    obj.setcover()


def test_class():
    instance = next(Image.new())
    new = Image(instance.id)
    assert new.good()
    assert new == instance


def test_load():
    objects = [next(Image.new())]
    owner = objects[-1].owner
    loaded = list(load_raw(owner))
    assert len(loaded)
    assert all(isinstance(x, Image) for x in loaded)
    assert all(x.owner == owner for x in loaded)
    assert all(x.good() for x in loaded)
    assert set(loaded) == set(objects)


def test_delete():
    obj = next(Image.new())
    owner = obj.owner
    Image.delete(owner, [obj])
    assert not Image(obj.id).good()