from bottle import response, redirect, request
from .. import consts
from ..el.accounts import auth


def main(*, current, loggedin, current_profile, **ka):
    if not loggedin:
        redirect('/auth/sign-in')
    return {}


def profile(*, current, loggedin, current_profile, **ka):
    if not loggedin:
        redirect('/auth/sign-in')

    return {'countries': consts.COUNTRIES}


def security(*, current, loggedin, current_profile, **ka):
    if not loggedin:
        redirect('/auth/sign-in')

    return {}


def sign_out(*, current, loggedin, **ka):
    if loggedin:
        auth.cookies.delete_tokens(current.tokens)
        response.delete_cookie(domain=request.environ.get('DOTTED_DOMAIN'), 
                               key='token', path='/')
        if not current.multi:
            response.delete_cookie(domain=request.environ.get('DOTTED_DOMAIN'),
                                   key='acid', path='/')
        else:
            response.set_cookie(domain=request.environ.get('DOTTED_DOMAIN'),
                                name='acid', path='/', value=current.acid[0],
                                max_age=current.acid[1])
    redirect('/')


def reset_with_key(current, loggedin, key, **ka):
    errors = []

    if key:
        reset = auth.Reset(key)
        newpwd = request.POST.get('new-pwd')

        if not reset.good():
            errors.append('The key is outdated / was already used / is just wrong')

        if newpwd and consts.PWD_LENGTH[0] <= len(newpwd) <= consts.PWD_LENGTH[1]:
            errors.append('Your password must contain from {0} to {1} chars,'
                          ' remember?'.format(*consts.PWD_LENGTH))
            
        if not errors:
            with reset.record as rec:
                rec.pwd = auth.hashed(newpwd)

            if not loggedin or reset.record not in current.accounts:
                ka = {'acct': reset.record}
                if loggedin:
                    ka['acid'] = current.acid[0]
                max_age = auth.cookie_age
                acid, token = auth.cookies.generate_and_save(**ka)
                response.set_cookie(domain=request.environ.get('DOTTED_DOMAIN'),
                                    name='token', value=token, path='/',
                                    max_age=max_age) 
            else:
                acid, max_age = current.acid

            response.set_cookie(domain=request.environ.get('DOTTED_DOMAIN'),
                                name='acid', value=acid, path='/', max_age=max_age)
            redirect('/')

        else:
            return {'errors': errors, 'POST': request.POST}


def reset_no_key(*, credentials, env, **ka):
    success, errors = [], []
    if credentials:
        if '@' in credentials:
            reset = auth.ResetNoKey(email=credentials)
            type_ = 'email address'
        else:
            reset = auth.ResetNoKey(name=credentials)
            type_ = 'name'

        if reset.good():
            reset.send(host=request.environ['HTTP_HOST'],
                       template=env.get_template('email/password-reset.html'))
            success.append('Roger that. Go check your mailbox.')
        else:
            errors.append('Provided {} was not found'.format(type_))

    return {'success': success, 'errors': errors, 'POST': request.POST}
