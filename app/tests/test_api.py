import pytest
import webtest
from uuid import uuid4
from contextlib import ExitStack
from pathlib import Path
from operator import attrgetter
from app.el.images import Image, raw as load_raw
from app.el.posts import Post, page
from app.el import notifications
from app.el.accounts.records import Record
from app.el.accounts import auth
from app.app import application as _application

application = webtest.TestApp(_application)
files = Path(__file__).parent / 'images'


@pytest.fixture(scope='function')
def api_authed():
    acct = Record.new()
    for name, value in acct.cookies.items():
        application.set_cookie(name, value)
    return acct


@pytest.mark.api
@pytest.mark.integration
class TestImages:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    @pytest.mark.skipif(pytest.config.getoption('--no-urls'), reason='Skipping urls')
    @pytest.mark.parametrize('url', 
        ['http://dummyimage.com/600x400/000/fff.gif',
         'http://dummyimage.com/600x400/000/fff.png',
         'http://dummyimage.com/600x400/000/fff.jpg'],
        ids=['GIF image', 'PNG image', 'JPG image']
    )
    @pytest.mark.slow
    def test_post_url(self, api_authed, url):
        req = application.post('/api/02/images?url={}'.format(url))
        assert req.status_int == 201
        assert req.json['success'], req.json

    @pytest.mark.skipif(pytest.config.getoption('--no-urls'), reason='Skipping urls')
    @pytest.mark.slow
    @pytest.mark.parametrize('url',
        ['http://dummyimage.com', '<string>', 'nonsense' ],
        ids=['HTML page', 'Empty string', 'nonsense']
    )
    def test_post_bad_url(self, api_authed, url):
        req = application.post('/api/02/images?url={}'.format(url))
        assert req.status_int == 200
        assert not req.json['success'], req.json

    @pytest.mark.parametrize('file', 
        [files / 'test.jpg', files / 'test.png', files / 'test.gif'],
        ids=['JPG images', 'PNG images', 'GIF images']
    )
    def test_post_plain(self, api_authed, file):
        # Test upload of multiple files
        with file.open('rb') as file1, file.open('rb') as file2:
            upload = [('image', '<string>', f.read()) for f in (file1, file2)]
            req = application.post('/api/02/images', upload_files=upload)
        assert req.status_int == 201
        assert req.json['success'], req.json

    @pytest.mark.parametrize('act', ['cover', 'avatar'], ids=['cover', 'avatar'])
    @pytest.mark.parametrize('num', [1, 2], ids=['1 image', '2 images'])
    @pytest.mark.parametrize('file', 
        [files / 'test.jpg', files / 'test.png', files / 'test.gif'],
        ids=['JPG images', 'PNG images', 'GIF images']
    )
    def test_post_set(self, api_authed, act, num, file):
        # I see no reason to split this function (e.g. into 
        # test_post_avatar and test_post_cover)
        url = '/api/02/images?set=' + act
        with ExitStack() as s:
            files = [s.enter_context(file.open('rb')) for _ in range(num)]
            req = application.post(url, upload_files=[
                                    ('image', '<string>', f.read()) for f in files
                                ])
        if num == 1 != file.suffix != '.gif':
            assert req.json['success'], req.json
            assert req.status_int == 201
            assert Image(req.json['id']).good()
        else:
            assert req.status_int == 200
            assert not req.json['success'], req.json

    def test_get_id(self):
        img = next(Image.new())
        req = application.get('/api/02/images?id={}'.format(img.id))
        assert req.status_int == 200
        assert req.json['success'], req.json
        assert Image(req.json['id']) == img
        
    def test_get_name(self):
        img = next(Image.new())
        req = application.get('/api/02/images?name=' + img.owner.name)
        assert req.status_int == 200
        assert req.json['success'], req.json

    def test_get(self, api_authed):
        img = next(Image.new(api_authed))
        req = application.get('/api/02/images')
        assert req.status_int == 200
        assert req.json['success'], req.json
        assert req.json['ids'] == [str(img.id)]

    def test_delete(self, api_authed):
        # Not using the fixture here
        # Test deletion of multiple images
        objects = [next(Image.new(api_authed))]
        req = application.delete_json('/api/02/images', 
                                      params={'ids': [str(x.id) for x in objects]})
        assert req.status_int == 200
        assert req.json['success'], req.json
        assert all(not Image(x.id).good() for x in objects)


@pytest.mark.api
@pytest.mark.integration
class TestPosts:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    @pytest.mark.parametrize('file', 
        [files / 'test.jpg', files / 'test.png', files / 'test.gif'],
        ids=['JPG images', 'PNG images', 'GIF images']
    )
    def test_post_plain(self, api_authed, file):
        # Test upload of multiple files
        with file.open('rb') as file1, file.open('rb') as file2:
            upload = [('image', '<string>', f.read()) for f in (file1, file2)]
            req = application.post('/api/02/posts',
                                   params={'content': '<string>'},
                                   upload_files=upload)
        assert req.status_int == 201
        assert req.json['success'], req.json
    
    @pytest.mark.parametrize('base_type', 
        [Image, Post],
        ids=['base image', 'base post']
    )
    def test_post_with_base(self, api_authed, base_type):
        base = base_type.new()
        # Won't fail for Image
        try:
            base = next(base)
        except TypeError:
            pass

        req = application.post('/api/02/posts', params={
                                'content': '<string>', 'id': base.id,
                                'type': base.type})
        assert req.status_int == 201
        assert req.json['success'], req.json
    
    def test_get(self, api_authed):
        req = application.get('/api/02/posts')
        assert req.status_int == 200
        assert req.json['success'], req.json
        assert 'html' in req.json
    
    def test_get_name(self, api_authed):
        post = Post.new(api_authed)
        req = application.get('/api/02/posts?name=' + post.owner.name)
        assert req.status_int == 200
        assert req.json['success'], req.json
        assert 'html' in req.json
        assert req.json['ids'] == [str(post.id)]
    
    def test_delete(self, api_authed):
        # Not using the fixture here
        objects = [Post.new(api_authed)]
        req = application.delete_json('/api/02/posts',
                                      params={'ids': [str(o.id) for o in objects]})
        assert req.status_int == 200
        assert req.json['success'], req.json
        assert all(not Post(o.id).good() for o in objects)


@pytest.mark.api
@pytest.mark.integration
class TestRecords:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    @pytest.mark.parametrize('by', ['id', 'name'], ids=['by id', 'by name'])
    def test_g(self, by):
        other, this = Record.new(), Record.new()
        req = application.get('/api/02/records?{}={}'.format(by, getattr(other, by)))
        assert req.status_int == 200
        assert req.json['success'], req.json
        assert req.json['record'].keys() <= other.as_public_dict().keys()

        for name, value in this.cookies.items():
            application.set_cookie(name, value)

        req = application.get('/api/02/records')
        assert req.status_int == 200
        assert req.json['success'], req.json
        assert req.json['record'].keys() <= this.as_public_dict().keys()

    def test_put_unset(self, api_authed):
        with api_authed as account:
            account.email = 'abc@12345.com'
            account.country = 'UK'
            account.website = '12345.com'
            account.real_name = 'Real name'

        params = ['email', 'country', 'website', 'real_name', 'fixed_post']
        req = application.put_json('/api/02/records/unset', params=params)
        assert req.status_int == 200
        assert req.json['success'], req.json

        account = Record(id=api_authed.id) # reload

        for x in params:
            assert getattr(account, x) is None

    def test_put_set(self, api_authed):
        params = {'email': '{}@12345.com'.format(uuid4()),
                  'country': 'gb',
                  'website': '12345.com',
                  'real_name': 'Real name',
                  'name': uuid4().hex}
        req = application.put_json('/api/02/records/set', params=params)
        assert req.status_int == 200
        assert req.json['success'], req.json

        account = Record(id=api_authed.id) # reload

        for k, v in params.items():
            assert getattr(account, k) == v

    @pytest.mark.slow
    def test_put_set_pwd(self, api_authed):
        params = {'pwd': {'old': api_authed.plaintext_pwd, 'new': '<string>'}}
        req = application.put_json('/api/02/records/set', params=params)
        assert req.status_int == 200
        assert req.json['success'], req.json
        account = Record(id=api_authed.id) # reload
        assert auth.signin(account, params['pwd']['new'])

    def test_put_combo(self, api_authed):
        # Minimal test, only test it doesn't fail
        # I don't (yet) see the need for a full blown test

        with api_authed as account:
            account.email = uuid4().hex + '@12345.com'

        params = {'unset': ['email'], 'set': {'real_name': 'Real name'}}
        req = application.put_json('/api/02/records', params=params)
        assert req.status_int == 200
        assert req.json['success'], req.json
        account = Record(id=api_authed.id) # reload
        assert account.email is None
        assert account.real_name == params['set']['real_name']


@pytest.mark.api
@pytest.mark.integration
class TestNotifications:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_get(self, api_authed):
        other = Record.new()
        # These types do no require anything other than `other`
        types = (notifications.FollowerNotification,
                 notifications.FriendNotification)
        ns = [t.new(api_authed, other=other) for t in types]
        req = application.get('/api/02/notifications')
        assert req.status_int == 200
        assert req.json['success'], req.json
        assert {str(x.id) for x in ns} == {x['id'] for x in req.json['notifications']}
        # TODO: Make `text` not empty in tests
        assert {x.get_text() for x in ns} == {x['text'] for x in req.json['notifications']}

    def test_delete(self, api_authed):
        other = Record.new()
        # These types do no require anything other than `other`
        types = (notifications.FollowerNotification,
                 notifications.FriendNotification)
        ns = [t.new(api_authed, other=other) for t in types]
        req = application.delete_json('/api/02/notifications', 
                                      params={'ids': [str(ns[0].id)]})
        assert req.status_int == 200
        assert req.json['success'], req.json

        assert list(notifications.load(api_authed))

        req = application.delete_json('/api/02/notifications')
        assert req.status_int == 200
        assert req.json['success'], req.json
        
        assert not list(notifications.load(api_authed))


@pytest.mark.api
@pytest.mark.integration
class TestRatings:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    @pytest.mark.parametrize('act',
        [('upvote', 1), ('downvote', -1), ('unvote', 0)],
        ids=['upvote', 'downvote', 'unvote']
    )
    @pytest.mark.parametrize('item_type',
        [Image, Post],
        ids=['image', 'post']
    )
    def test_put(self, api_authed, item_type, act):
        action, change = act
        item = item_type.new(api_authed)
        # Won't fail for Image
        try:
            item = next(item)
        except TypeError:
            pass

        path = '/api/02/ratings/{}?{}={}'.format(
                action, 'post' if isinstance(item, Post) else 'image', item.id)
        req = application.put_json(path)
        assert req.status_int == 200
        ri = item_type(item.id)
        assert req.json['success'], req.json
        assert ri.score - item.score == change


@pytest.mark.api
@pytest.mark.integration
class TestRelations:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    @pytest.mark.parametrize('by', ['id', 'name'], ids=['by id', 'by name'])
    @pytest.mark.parametrize('act',
        ('follow', 'unfollow', 'block', 'unblock'),
        ids=('follow', 'unfollow', 'block', 'unblock')
    )
    def test_put(self, api_authed, act, by):
        acct = Record.new()
        req = application.put_json(
                '/api/02/relations/{}?{}={}'.format(act, by, getattr(acct, by))
            )
        assert req.status_int == 200
        assert req.json['success'], req.json
