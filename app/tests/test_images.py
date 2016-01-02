import pytest
import webtest
from pathlib import Path
from app.el.images import Image
from app.el.accounts.records import Record
import urllib.error

files = Path(__file__).parent / 'images'


@pytest.mark.parametrize('file', 
    [files / 'test.jpg', files / 'test.png', files / 'test.gif'],
    ids=['JPG images', 'PNG images', 'GIF images']
)
def test_create(file):
    acct = Record.new()
    with file.open('rb') as file1, file.open('rb') as file2:
        objects = []
        for f in [file1, file2]:
            try:
                objects.append(Image.new(acct, file1,
                                            allow_gif=file.suffix == '.gif'))
            except ValueError:
                continue
    assert len(objects)
    # True with allow_gif = True
    assert len(objects) == 2
    assert all(isinstance(x, Image) for x in objects)
    assert all(x.owner == acct for x in objects)
    assert all(x.good() for x in objects)

    if file.suffix == '.gif':
        with file.open('rb') as f:
            with pytest.raises(ValueError):
                Image.new(acct, f, allow_gif=False)


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
    downloaded = Image.new(acct, url, allow_gif=True)
    assert downloaded.good()
    assert downloaded.owner == acct
    assert isinstance(downloaded, Image)


@pytest.mark.skipif(pytest.config.getoption('--no-urls'), reason='Skipping urls')
@pytest.mark.parametrize('url',
    ['', 'nonsense'],
    ids=['Empty string', 'nonsense']
)
@pytest.mark.slow
def test_downloading_bad_urls(url):
    acct = Record.new()
    with pytest.raises(urllib.error.URLError):
        Image.new(acct, url, allow_gif=True)


@pytest.mark.skipif(pytest.config.getoption('--no-urls'), reason='Skipping urls')
@pytest.mark.parametrize('url',
    ['http://dummyimage.com'], # TODO: Add more types?
    ids=['HTML page']
)
@pytest.mark.slow
def test_downloading_bad_url_types(url):
    acct = Record.new()
    with pytest.raises(ValueError):
        Image.new(acct, url, allow_gif=True)


@pytest.mark.parametrize('file', 
    [files / 'test.jpg', files / 'test.png', files / 'test.gif'],
    ids=['JPG images', 'PNG images', 'GIF images']
)
def test_set(file):
    # Test setcover and setavatar methods
    with file.open('rb') as f:
        new = Image.new(Record.new(), f, allow_gif=file.suffix == '.gif')
    reload = Image(id=new.id, load_file=True)
    reload.setavatar()
    reload.setcover()


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