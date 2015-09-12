import functools
import json
import collections.abc
from ... import consts
from ...el.accounts import records, auth, relations
from ...el.accounts.profile import profile
from ...el.misc import utils
from ...el.misc.errors import api as ae
from ...el import ratings, images, posts, notifications
from ...bottle import request, response


def apiv2(func):
    @functools.wraps(func)
    def wrapper(**ka):
        output = {'success': 0, 'errors': []}
        merr = ae.MultiError()
        try:
            result = func(errors=merr, **ka)
            merr.raise_all()
        except ae.MultiError as e:
            if len(e.args) > 1:
                output['text'] = 'There were {} errors'.format(len(e.args))
            else:
                output['text'] = 'There was an error'

            for exc in e.exc:
                output['errors'].append({'text': str(exc), 'description': exc.description})
        else:
            output['success'] = 1
            if isinstance(result, collections.abc.Mapping):
                output.update(result)

            output.setdefault('text', 'The request was succesfully completed')

        return output
    return wrapper


@apiv2
def images_post(*, current, loggedin, errors, **ka):
    # Set the uploaded image as a cover or avatar
    change = request.query.get('set')
    # All images sent via POST
    submitted = request.files.getall('image')
    # The URL to download image from
    url = request.query.get('url')
    # Public image ID
    image_id = request.query.get('id')

    if not loggedin:
        errors.add(ae.NoAuth())

    if not (submitted or url or image_id):
        errors.add(ae.NothingToUpload())

    if change in {'cover', 'avatar'}:
        if len(submitted) + bool(url) + bool(image_id) != 1:
            errors.add(ae.Ambiguous('Do not know which image to use'))

        errors.raise_all()

        if image_id:
            image = images.Image(image_id, file=True)
            # FIXME: Split?
            if not image.good() or image.file.format == 'GIF':
                errors.add(ae.UnsupportedImageType('Image does not exist'
                                                      ' or its type is GIF'))
        else:
            file = [url if not submitted else submitted[0].file]
            image = next(images.Image.new(current.record, file), None)
            if image is None:
                # XXX:FIXME: Something meaningful would be good.
                errors.add(ae.PartialSuccess(0, 1))

        errors.raise_all()

        if change == 'avatar':
            with current.record as rec:
                rec.avatar = image.id
            image.setavatar()
            types = (consts.SQUARE_THUMBNAIL, consts.ORIGINAL_IMAGE, consts.AVATAR)
            response.status = 201
            return {
                'id': str(image.id), 
                'urls': images.urls_dict(image.name, types)
            }
        else:
            with current.record as rec:
                rec.cover = image.id
            image.setcover()
            response.status = 201
            return {
                'id': str(image.id),
                'urls': images.urls_dict(image.name, types=(consts.COVER_IMAGE,))
            }
    else:
        errors.raise_all()

        files = [x.file for x in submitted]

        # We currently allow only one URL per request, but
        # that can be changed in a nearest future
        if url:
            files.append(url)

        objects = list(images.Image.new(current.record, files, allow_gif=True))
        if len(files) - len(objects):
            # XXX:FIXME: Something meaningful would be good.
            errors.add(ae.PartialSuccess(len(objects), len(files)))
        else:
            types = (consts.SQUARE_THUMBNAIL, consts.ORIGINAL_IMAGE)
            response.status = 201
            return {
                'id': [str(x.id) for x in objects],
                'urls': [images.urls_dict(x.name, types) for x in objects]
            }


@apiv2
def images_get(*, current, loggedin, env, errors, **ka):
    # Public image ID
    image_id = request.query.get('id')
    # Account name
    # XXX: Add account ID as well?
    name = request.query.get('name')


    if image_id is not None:
        load_prof = request.query.get('profile', '0')
        showcase = request.query.get('profile', '1')
        if load_prof not in {'0', '1'}:
            errors.add(ae.BadValue('profile'))

        if showcase not in {'0', '1'}:
            errors.add(ae.BadValue('showcase'))

        image = images.Image(image_id, file=True)
        if not image.good():
            errors.add(ae.NotFound('image'))

        if not errors:
            retval = {
                'id': str(image.id),
                'dimensions': image.file.size,
                'urls': images.urls_dict(image.name, types=(consts.ORIGINAL_IMAGE,))
            }
            if load_prof == '1':
                retval['owner'] = profile(image.owner, public=True)
                retval['owner'].pop('avatar')
                retval['owner'].pop('cover')

            if showcase == '1':
                tpl_func = env.get_template('macros/showcase.html').module.image_showcase
                retval['showcase'] = tpl_func(image, profile(image.owner), retval['urls'])
            return retval
            
    elif name is not None or loggedin:
        # Size (in pixels)
        try:
            size = int(request.query.get('size', 100))
        except ValueError:
            errors.add(ae.BadValue('size'))

        # Number of images
        try:
            number = int(request.query.get('number', 25))
        except ValueError:
            errors.add(ae.BadValue('number'))

        if loggedin and (name is None or current.record.name == name):
            acct = current.record
        elif name is not None:
            acct = records.Record(name=name)
        else:
            acct = None

        if acct is None or not acct.good():
            errors.add(ae.NotFound('person'))

        if not errors:
            # Type of the images, that's right - no validation/processing here
            if not request.query.type or request.query.type == consts.SQUARE_THUMBNAIL:
                img_type = consts.SQUARE_THUMBNAIL
            else:
                img_type = consts.ORIGINAL_IMAGE
            tpl = env.get_template('macros/image.html')
            tpl_func = functools.partial(tpl.module.uniform_image, width=size, height=size)
            url_func = functools.partial(utils.image_url, type=img_type)
            objects = list(images.raw(acct, number=number))
            return {'ids': [str(o.id) for o in objects], 
                    'markup': [tpl_func(object=o, url=url_func(name=o.name)) for o in objects]}

    else:
        errors.add(ae.NoAuth())


@apiv2
def images_delete(*, current, loggedin, errors, **ka):
    # Multiple IDs
    data = request.body.read().decode('utf-8')

    if not loggedin:
        errors.add(ae.NoAuth())

    if not data:
        errors.add(ae.NothingToDelete())

    if not errors:
        try:
            ids = json.loads(data)['ids']
            if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            # FIXME: Meaningful message
            errors.add(ae.BadValue('ids'))
        else:
            images.Image.delete(current.record, ids)
            # BUG: Won't delete derived

@apiv2
def posts_post(*, current, loggedin, errors, env, **ka):
    # All files sent
    files = request.POST.getall('attachment')
    # Post content
    content = request.POST.get('content')

    if content is not None:
        content = utils.line_breaks(content.strip())
    
    if request.POST.get('id'):
        item, itype = request.POST.id, request.POST.type
    elif request.query.get('id'):
        item, itype = request.query.id, request.query.type
    else: # For obviousness, can be shortened:
        item, itype = None, None

    # TODO: return error if only one is provided
    if item and itype:
        try:
            itype = int(itype)
            if itype not in {consts.CONTENT_IMAGE, consts.CONTENT_POST}:
                raise ValueError
        except ValueError:
            errors.add(ae.BadValue('type'))
        else:
            if itype == consts.CONTENT_IMAGE:
                base = images.Image(item)
            else:
                base = posts.Post(item)
    else:
        base = None

    if not loggedin:
        errors.add(ae.NoAuth())

    if content and len(content) > consts.POST_MAXLENGTH:
        errors.add(ae.PostTooLong(len(content) - consts.POST_MAXLENGTH))

    if not errors:
        # More attachment types are comming
        imgs = list(images.Image.new(current.record, (x.file for x in files), 
                                     allow_gif=True))
        try:
            new = posts.Post.new(current.record, content=content, images=imgs,
                                 ext=base)
        except ValueError:
            errors.add(ae.EmptyPost())
        else:
            # TODO: return something
            response.status = 201
            posts.push(new, tpl=env.get_template('snippets/posts-api.html'),
                       types='all', current=current.record)
            notifications.emit_item(new, tpl=env.get_template('macros/notifications.html'))


@apiv2
def posts_get(*, current, loggedin, errors, env, **ka):
    try:
        number = int(request.query.get('number', 25))
    except ValueError:
        errors.add(ae.BadValue('number'))

    # Public ID of post to start loading from
    start = request.query.get('start')
    if start is not None:
        instance = posts.Post(start)
        if not instance.good():
            errors.add(ae.BadValue('start'))
        else:
            start = instance.id

    # Load posts for this account name
    name = request.query.get('name')

    if loggedin and (name is None or current.record.name == name):
        acct = current.record
    elif name is not None:
        acct = records.Record(name=name)
    else:
        acct = None

    if acct is None or not acct.good():
        errors.add(ae.NotFound('person'))

    if not errors:
        info = list(posts.iter_info(posts.page(acct, number)))
        data = {'posts': info, 'current': current}
        ids = [str(x.id) for x in info]
        return {'html': env.get_template('snippets/posts-api.html').render(data),
                'ids': ids}


@apiv2
def posts_delete(*, current, loggedin, errors, **ka):
    # Multiple IDs
    data = request.body.read().decode('utf-8')

    if not loggedin:
        errors.add(ae.NoAuth())

    if not data:
        errors.add(ae.NothingToDelete())

    if not errors:
        try:
            ids = json.loads(data)['ids']
            if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            # FIXME: Meaningful message
            errors.add(ae.BadValue('ids'))
        else:
            posts.Post.delete(current.record, ids)


@apiv2
def notifications_get(*, current, loggedin, errors, **ka):
    if not loggedin:
        errors.add(ae.NoAuth())
    else:
        ns = list(notifications.load(current.record))
        return {'notifications': [{'id': str(n.id), 'text': n.get_text()} for n in ns]}


@apiv2
def notifications_delete(*, current, loggedin, errors, **ka):
    data = request.body.read().decode('utf-8')

    if not loggedin:
        errors.add(ae.NoAuth())

    errors.raise_all()

    if not data:
        notifications.Notification.delete_unread(current.record)
    else:
        try:
            ids = json.loads(data)['ids']
            if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            errors.add(ae.BadValue('ids'))
        else:
            notifications.Notification.delete(current.record, ids)


@apiv2
def ratings_put(*, action, current, loggedin, errors, **ka):
    image = request.query.get('image')
    post = request.query.get('post')

    if not loggedin:
        errors.add(ae.NoAuth())

    if not image and not post:
        errors.add(ae.NothingToRate(action))

    if action not in {'upvote', 'downvote', 'unvote'}:
        errors.add(ae.UnknownAction(action))

    errors.raise_all()
    
    item = images.Image(image) if image else posts.Post(post)
    if not item.good():
        errors.add(ae.NotFound('image' if image else 'post'))

    errors.raise_all()

    if action != 'unvote' and relations.is_blocked(item.owner, current.record):
        errors.add(ae.NotPermitted('You\'re blocked and can\'t vote on this '
                                   'person\'s content'))

    errors.raise_all()

    # TODO: Disallow disallowing downvotes?
    # if action == 'downvote' and not item.owner.downvotes:
    #     errors.add(ae.NotPermitted('This person has disallowed downvotes on '
    #                                'their content'))

    errors.raise_all()

    try:
        func = getattr(ratings, action[:-4])
    except AttributeError:
        pass
    else:
        func(current.record, item)
        return {'new': item.score}

@apiv2
def relations_put(*, action, current, loggedin, errors, **ka):
    name = request.query.get('name')
    _id = request.query.get('id') # TODO: tests

    if not loggedin:
        errors.add(ae.NoAuth())

    if name is None and _id is None:
        errors.add(ae.NoParams())

    errors.raise_all()

    ka = {'name': name} if name else {'id': _id}
    acct = records.Record(**ka)

    if not acct.good():
        errors.add(ae.NotFound('person'))

    if action == 'follow':
        if relations.is_follower(current.record, acct):
            return {'text': 'You already follow this user'}
        else:
            relations.follow(current.record, acct)
            return {'text': 'You\'re now following this user'}

    elif action == 'unfollow':
        if relations.is_follower(current.record, acct):
            relations.unfollow(current.record, acct)
            return {'text': 'Unfollowed'}
        else:
            return {'text': 'You are not following tha user'}

    elif action == 'block':
        if relations.is_blocked(current.record, acct):
            return {'text': 'You\re already blocking this user'}
        else:
            relations.block(current.record, acct)
            return {'text': 'You are now blocking this user'}

    elif action == 'unblock':
        if relations.is_blocked(current.record, acct):
            relations.block(current.record, acct)
            return {'text': 'You\re now blocking this user'}
        else:
            return {'text': 'You are not blocking this user'}

    else:
        errors.add(ae.UnknownAction(action))


@apiv2
def records_get(*, current, loggedin, errors, **ka):
    name = request.query.get('name')
    _id = request.query.get('id')

    if name is None and _id is None:
        # FIXMEEEEEE
        pd = current.record.as_public_dict()
        pd.pop('profile')
        return {'record': pd}

    ka = {'name': name} if name else {'id': _id}
    acct = records.Record(**ka)

    if not acct.good():
        errors.add(ae.NotFound('person'))
    else:
        return {'record': acct.as_public_dict()}
        

def _name_validation(value, this):
    if not utils.name_format(value):
        yield ae.WrongFormat('name')

    rec = records.Record(name=value)
    if rec.good() and rec != this:
        yield ae.Taken('name')


def _email_validation(value, this):
    if not consts.EMAIL_LENGTH[0] <= len(value) <= consts.EMAIL_LENGTH[1] or \
       not utils.email_format(value):
       yield ae.WrongFormat('email')
    rec = records.Record(email=value)       
    if rec.good() and rec != this:
        yield ae.Taken('email')
    
def _pwd_validation(old, new, this):
    if old is None or new is None:
        yield ae.NotEnoughParams('Missing old and/or new password')
    else:
        if not (consts.PWD_LENGTH[0] <= len(new) <= consts.PWD_LENGTH[1]):
            yield ae.WrongFormat('password')

        if not auth.signin(this, old):
            yield ae.IncorrectPassword()



@apiv2
def records_put(*, action, current, loggedin, errors, **ka):
    unsettable = {'real_name', 'email', 'country', 'website', 'fixed_post'}
    updateable = unsettable | {'name', 'email', 'pwd'}
    data = request.body.read().decode('utf-8')

    mod = {'unset': set(), 'set': {}}

    try:
        parsed = json.loads(data)
        if action == 'unset':
            if not isinstance(parsed, list):
                raise ValueError
            mod['unset'].update(parsed)
        elif action == 'set':
            if not isinstance(parsed, dict):
                raise ValueError
            mod['set'].update(parsed)
        elif action is None:
            for k, v in mod.items():
                if k in parsed:
                    v.update(parsed[k])
    except (ValueError, KeyError, TypeError):
        errors.add(ae.BadValue('XXX'))

    if not loggedin:
        errors.add(ae.NoAuth())

    if not data:
        errors.add(ae.NoParams())

    if action and action not in {'set', 'unset'}:
        errors.add(ae.BadValue('action'))

    errors.raise_all()

    upd = {k: v for k, v in mod['set'].items() if k in updateable}

    if 'email' in upd:
        ws = list(_email_validation(upd['email'], current.record))
        if ws:
            for w in ws:
                errors.add(w)
            upd.pop('email')

    if 'pwd' in upd:
        old, new = upd['pwd'].get('old'), upd['pwd'].get('new')
        ws = list(_pwd_validation(old, new, current.record))
        if ws:
            for w in ws:
                errors.add(w)
            upd.pop('pwd')
        else:
            upd['pwd'] = auth.hashed(new)

    if 'name' in upd:
        ws = list(_name_validation(upd['name'], current.record))
        if ws:
            for w in ws:
                errors.add(w)
            upd.pop('name')

    if 'country' in upd:
        if upd['country'] not in consts.COUNTRIES:
            errors.add(ae.WrongFormat('country'))
            upd.pop('country')

    if 'real_name' in upd:
        if len(upd['real_name']) > consts.NAME_MAXLENGTH:
            errors.add(ae.WrongFormat('real_name'))
            upd.pop('real_name')

    if 'website' in upd:
        if not (consts.WEBSITE_LENGTH[0] <= len(upd['website']) <= consts.WEBSITE_LENGTH[1]) or \
           not utils.getall_urls(upd['website']):
           errors.add(ae.WrongFormat('website'))
           upd.pop('website')

    if 'fixed_post' in upd:
        post = posts.Post(upd['fixed_post'])
        if not post.good():
            errors.add(ae.NotFound('post'))
            upd.pop('fixed_post')

    with current.record as rec:
        for field in mod['unset'] & unsettable:
            setattr(rec, field, None)

        for field, value in upd.items():
            setattr(rec, field, value or None)
