import sys
import functools
from ..el.accounts import auth, records, relations
from ..el.accounts.profile import profile
from ..el import posts, images
from ..el.misc import utils
from .. import consts
from . import api, accounts

from bottle import request, redirect, response, abort

__all__ = ['index', 'sign_in', 'sign_up', 'profile', 'api', 'accounts']


def index(*, current, loggedin, **ka):
    if loggedin:
        feedit = posts.Feed.get(current.record)
        return {'feed': posts.iter_info(feedit)}
    return {}


def sign_in(*, current, loggedin, **ka):
    name, pwd, remember = (request.POST.get(x) for x in ('name', 'pwd', 'remember'))
    errors = []

    if name and pwd:
        acct = records.Record(name=name)
        if not acct.good():
            errors.append('There\'s no such account')
        elif not auth.signin(acct, pwd):
            errors.append('Provided credentials did not match any record')
        else:
            ka = {'acct': acct, 'session': not remember}
            if loggedin: 
                ka['acid'] = current.acid[0]
            acid, token = auth.cookies.generate_and_save(**ka)

            if not remember:
                if loggedin:
                    max_age = max(current.max_ttl, auth.session_age)
                else:
                    max_age = auth.session_age
            else:
                # current.max_ttl can't be bigger than auth.cookie_age
                max_age = auth.cookie_age

            response.set_cookie(domain=request.environ.get('DOTTED_DOMAIN'),
                                max_age=max_age, name='token'   , value=token, path='/')
            response.set_cookie(domain=request.environ.get('DOTTED_DOMAIN'),
                                max_age=max_age, name='acid', value=acid, path='/')
            redirect('/')

    return {'errors': errors, 'POST': request.POST, 'switch': request.query.switch}


def sign_up(*, current, loggedin, **ka):
    name, pwd = request.POST.get('name'), request.POST.get('pwd')
    errors = []

    if name and pwd:
        if not (consts.PWD_LENGTH[0] <= len(pwd) <= consts.PWD_LENGTH[1]):
            errors.append('Your password must contain'
                          ' from {} to {}'.format(*consts.PWD_LENGTH))

        if not utils.name_format(name):
            errors.append('#TODO: Update the message')

        if not errors:
            try:
                acct = auth.signup(name, pwd)
            except ValueError:
                errors.append('The name {!r} is already present'.format(name))
            else:
                ka = {'acct': acct}
                if loggedin: 
                    ka['acid'] = current.acid[0]
                acid, token = auth.cookies.generate_and_save(**ka)

                response.set_cookie(domain=request.environ.get('DOTTED_DOMAIN'),
                            max_age=auth.cookie_age, name='token', value=token, path='/')

                response.set_cookie(domain=request.environ.get('DOTTED_DOMAIN'),
                            max_age=auth.cookie_age, name='acid', value=acid, path='/')

                redirect('/')

    return {'errors': errors, 'POST': request.POST, 'switch': request.query.switch}


def profile_page(*, current, loggedin, name, env, **ka):
    page = records.Record(name=name)        
    if not page.good():
        abort(404)

    retvars = {}
    page_profile = profile(page, minimal=False)
    if page_profile.get('fixed_post'):
        fixed = posts.Post(page_profile['fixed_post'])
        if fixed.good():
            # There's exactly 1 element, safe to subscript
            page_profile['fixed_post'] = posts.iter_info([fixed])[0]
        else:
            with page:
                page.fixed_post = None

    rels = {}
    if loggedin:
        # Is `current.record` blocked by `page`?
        rels['is_blocked'] = relations.is_blocked(page, current.record)
        # Is `page` blocked by `current.record`?
        rels['has_blocked'] = relations.is_blocked(current.record, page)

        # Friends don't block friends
        if not rels['is_blocked'] and not rels['has_blocked']:
            rels['are_friends'] = relations.are_friends(current.record, page)
        else:
            rels['are_friends'] = False

        # Friends follow each other
        if not rels['are_friends']:
            rels['following'] = relations.is_follower(current.record, page)
            rels['followee'] = relations.is_follower(page,  current.record)
        else:
            rels['followee'], rels['following'] = True, True

    url_func = functools.partial(utils.image_url, type=consts.SQUARE_THUMBNAIL)
    page_images = [o.add({'url': url_func(name=o.name)}) for o in images.raw(page)]
    
    posts_it = posts.iter_info(posts.page(page))
    return {'relations': rels, 'page_profile': page_profile, 'page_record': page,
            'page_images': page_images, 'page_posts': list(posts_it)}


def people(*, current, loggedin, **ka):
    return {'people': [x.add({'profile': profile(x)}) for x in records.number()]}
    

def images_page(*, current, loggedin, **ka):
    if not loggedin:
        redirect('/auth/sign-in')
    else:
        url_func = functools.partial(utils.image_url, type=consts.SQUARE_THUMBNAIL)
        objects = list(images.raw(current.record))
        return {'images': [o.add({'url': url_func(name=o.name)}) for o in objects]}
