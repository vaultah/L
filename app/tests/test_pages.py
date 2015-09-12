import pytest
import webtest
import uuid
from app.app import application as _application
from app.el.accounts.records import Record

application = webtest.TestApp(_application)

def setup_function(func):
    application.reset()

teardown_function = setup_function

# TODO: Test switch and bad data (parametrize)


@pytest.fixture(scope='function')
def authed():
    acct = Record.new()
    for name, value in acct.cookies.items():
        application.set_cookie(name, value)
    return acct


@pytest.mark.integration
class TestMain:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_nonlogged(self):
        main = application.get('/')
        assert main.status_int == 200

    def test_logged(self, authed):
        main = application.get('/')
        main.mustcontain('Sign out')
        assert main.status_int == 200


@pytest.mark.slow
@pytest.mark.integration
class TestSignUp:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_get(self):
        assert application.get('/auth/sign-up').status_int == 200

    def test_post(self):
        params = {'url': '/auth/sign-up',
                  'params': {'name': uuid.uuid4().hex, 'pwd': '<string>'}}
        # Succesful sign up
        resp = application.post(**params)
        assert resp.status_int == 302


@pytest.mark.slow
@pytest.mark.integration
class TestSignIn:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_get(self):
        assert application.get('/auth/sign-in').status_int == 200

    def test_post(self):
        acct = Record.new()
        params = {'url': '/auth/sign-in',
                  'params': {'name': acct.name, 'pwd': '<string>'}}

        # Test wrong name, pwd combination
        resp = application.post(**params)
        assert resp.status_int == 200

        # Succesful sign up
        params['params']['pwd'] = acct.plaintext_pwd
        resp = application.post(**params)
        assert resp.status_int == 302


@pytest.mark.integration
class TestSignOut:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_nonlogged(self):
        assert application.get('/auth/sign-out').status_int == 302

    def test_logged(self, authed):
        assert application.get('/auth/sign-out').status_int == 302


@pytest.mark.integration
class TestPasswordReset:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_nonlogged(self):
        assert application.get('/auth/reset').status_int == 200

    def test_logged(self, authed):
        assert application.get('/auth/reset').status_int == 200


@pytest.mark.integration
class TestProfile:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_nonlogged(self):
        acct = Record.new()
        prof = application.get('/' + acct.name)
        assert prof.status_int == 200
        prof.mustcontain(acct.name)

        unk = application.get('/' + uuid.uuid4().hex, expect_errors=True)
        assert unk.status_int == 404

    def test_logged(self, authed):
        prof = application.get('/' + authed.name)
        assert prof.status_int == 200
        prof.mustcontain(authed.name)


@pytest.mark.integration
class TestPeople:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_nonlogged(self):
        assert application.get('/people').status_int == 200

    def test_logged(self, authed):
        people = application.get('/people')
        assert people.status_int == 200
        people.mustcontain(authed.name)


@pytest.mark.integration
class TestImages:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_nonlogged(self):
        # Redirects to /auth/sign-in if is not logged
        assert application.get('/images').status_int == 302

    def test_logged(self, authed):
        assert application.get('/images').status_int == 200


@pytest.mark.integration
class TestAccount:

    def setup_method(self, method):
        application.reset()

    teardown_method = setup_method

    def test_main(self):
        assert application.get('/account').status_int == 302

    def test_main_logged(self, authed):
        acc = application.get('/account')
        assert acc.status_int == 200
        acc.mustcontain(authed.name)

    def test_profile(self):
        assert application.get('/account/profile').status_int == 302

    def test_profile_logged(self, authed):
        assert application.get('/account/profile').status_int == 200

    def test_security(self):
        assert application.get('/account/security').status_int == 302

    def test_security_logged(self, authed):
        assert application.get('/account/security').status_int == 200


