'''
Router script. Handles all requests and passes them to the automatically
imported controllers. This is also required by WSGI
server (`--wsgi-file` option for uWSGI).
'''

import os
import re
import sys
import importlib
import jinja2
import functools

from .el.misc import utils
from . import consts
from bottle import request, hook, default_app, get, post, \
                   route, debug, response, abort, url, redirect

from . import jinja2htmlcompress
env = jinja2.Environment(extensions=[jinja2htmlcompress.HTMLCompress],
                         loader=jinja2.FileSystemLoader(str(consts.L_VIEWS)))

# Make constants global, the regex is pretty self-explanatory
_const = re.compile('^[A-Z_]+$')
env.globals.update((k, v) for k, v in vars(consts).items() if _const.match(k))

from .el.accounts import auth, profile
from .el.accounts.records import Record
from .el.notifications import load as load_notifications
from . import controllers


@hook('before_request')
def set_environ():
    request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')
    # HTTP_HOST seems to be appropriate for the job,
    # I see no need for SERVER_NAME
    try:
        request.environ['DOTTED_DOMAIN'] = '.{host}'.format(host=request.environ["HTTP_HOST"])
    except KeyError:
        request.environ['DOTTED_DOMAIN'] = ''


def view(name):
    presets = {}
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            tpl_vars = {}
            tpl_vars.update(presets)
            if response:
                tpl_vars.update(response.copy())
            return env.get_template(name).render(**tpl_vars)
        return wrapper
    return decorator


def common(json=False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*a, **kw):
            # Update the arguments with those we need in the function
            params = kw.copy()
            this = auth.Current(acid=request.cookies.get('acid'),   
                                token=request.cookies.get('token'))
            switch = request.query.get('switch')
            if switch is not None:
                _route_name = request['bottle.route'].name
                acct = Record(name=switch)
                if not acct.good():
                    if _route_name != 'sign_up':
                        redirect(url('sign_up', switch=switch))
                elif acct == this.record:
                    if _route_name != 'main':
                        redirect(url('main'))
                elif acct in this.records:
                    this.switch_to(acct)
                    if _route_name != 'main':
                        redirect(url('main'))
                else:
                    if _route_name != 'sign_in':
                        redirect(url('sign_in', switch=switch))

            if this.loggedin:
                # That's right, set the ACID cookie on every request
                response.set_cookie(name='acid', path='/', max_age=this.acid[1],
                                    value=this.acid[0],
                                    domain=request.environ.get('DOTTED_DOMAIN'))
                
                if this.set_token:
                    response.set_cookie(name='token', max_age=this.token[1], value=this.token[0],
                                        domain=request.environ.get('DOTTED_DOMAIN'), path='/')

            if this.loggedin:
                nots = {x.id: x.get_html(env.get_template('macros/notifications.html'))
                        for x in load_notifications(this.record)}
            else:
                nots = {}

            params.update(
                current=this,
                current_profile=profile.profile(this.record) if this.loggedin else {},
                notifications=nots,
                accounts=[x.add({'profile': profile.profile(x)}) for x in this.records],
                loggedin=this.loggedin,
                env=env # TODO: Not sure. Most certainly not the best solution
            )
            result = func(*a, **params)

            if json:
                return result
            elif isinstance(result, dict):
                params.update(result)
                return params
            else:
                return result
                
        return wrapper
    return decorator


@get('/', name='main')
@view('main-logged.html')
@common()
def index_page(**ka):
    return controllers.index(**ka)


@route('/auth/sign-in', method=['POST', 'GET'], name='sign_in')
@view('/auth/sign-in.html')
@common()
def sign_in_page(**ka):
    return controllers.sign_in(**ka)


@route('/auth/sign-up', method=['POST', 'GET'], name='sign_up')
@view('/auth/sign-up.html')
@common()
def sign_up_page(**ka):
    return controllers.sign_up(**ka)


@route('/people', method=['GET'])
@view('people.html')
@common()
def people_page(**ka):
    return controllers.people(**ka)


@route('/images', method=['GET'])
@view('images.html')
@common()
def images_page(**ka):
    return controllers.images_page(template=env.get_template('macros/image.html'),
                                   **ka)


@route('/<name>', method=['GET'])
@view('profile.html')
@common()
def profile_page(**ka):
    return controllers.profile_page(template=env.get_template('macros/image.html'),
                                    **ka)


@get('/account')
@view('account/main.html')
@common()
def account_main(**ka):
    return controllers.accounts.main(**ka)


@get('/account/profile')
@view('account/profile.html')
@common()
def account_main(**ka):
    return controllers.accounts.profile(**ka)


@get('/account/security')
@view('account/security.html')
@common()
def account_main(**ka):
    return controllers.accounts.security(**ka)


@get('/auth/sign-out')
@common()
def account_main(**ka):
    return controllers.accounts.sign_out(**ka)


@route('/auth/reset', method=['POST', 'GET'])
@view('auth/reset.html')
@common()
def reset_no_key(**ka):
    return controllers.accounts.reset_no_key(credentials=request.POST.reset,
                                             **ka)


@route('/auth/reset/<key>', method=['POST', 'GET'])
@view('auth/reset-key.html')
@common()
def reset_key(**ka):
    return controllers.accounts.reset_with_key(**ka)


@route('/api/<version>/<part>', ['PUT', 'GET', 'POST', 'DELETE'])
@route('/api/<version>/<part>/<action>', ['PUT', 'GET', 'POST', 'DELETE'])
def main_api(version, part, action=None):
    try:
        api = importlib.import_module('.controllers.api.api_v{}'.format(version), 'app')
        pieces = [part, request.method.lower()]
        func = getattr(api, '_'.join(pieces))
    except (ImportError, AttributeError):
        abort(404)
    else:
        return common(json=True)(func)(action=action)


application = default_app()
debug()


