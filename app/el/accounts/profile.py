from . import records
from ..misc import utils
from .. import images
from ... import consts
import collections


def profile(acct, *, minimal=True, public=False):
    ''' Get the profile info for `acct` and return a `dict` 
        if minimal is truthy, skip processing country, website etc. '''
            
    if not isinstance(acct, records.Record):
        raise TypeError
        
    if not acct.good():
        raise ValueError('Unable to get profile info, record is not present')

    # Returns None for missing fields
    if public:
        rv = acct.as_public_dict()
    else:
        rv = acct.as_dict()

    rv['avatar'] = {}
    if acct.avatar:
        av = images.Image(acct.avatar, file=False)
        if av.good():
            rv['avatar']['id'] = av.id
            types = (consts.SQUARE_THUMBNAIL, consts.ORIGINAL_IMAGE, 
                     consts.AVATAR)
            rv['avatar'].update(images.urls_dict(av.name, types))

    # Additional info if the full profile was requested
    if not minimal:
        rv['website_link'] = 'http://{}'.format(acct.website) if acct.website else None
        rv['country_name'] = consts.COUNTRIES.get(acct.country)
        if acct.cover is not None:
            cover = images.Image(acct.cover, file=False)
            if cover.good():
                rv['cover'] = utils.image_url(name=cover.name, type=consts.COVER_IMAGE)

    return rv