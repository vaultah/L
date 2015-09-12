import os
import ssl
import time
import re
import uuid
import hashlib
import sha3 # Check if we can drop this
import random
from html import escape
from datetime import datetime
from ... import consts
from pathlib import PurePath


def image_url(**ka):
    defs = {'schema': 'http',
            'domain': consts.L_MEDIA_DOMAIN,
            'images': consts.IMAGES_DIR,
            'type': ka.get('type', consts.ORIGINAL_IMAGE),
            'name': ka['name']}

    return '{schema}://{domain}/{images}/{type}/{name}'.format_map(defs)

_mentions_re = r'(?<=\*)[{2}]{{{0},{1}}}(?![{2}])'.format(
                        *consts.USR_LENGTH + [re.escape(''.join(consts.NAME_CHARACTERS))]
                    )
_mentions_compl = re.compile(_mentions_re)
def mentions(source):
    ''' Use regex to find all mentioned accounts in `source` '''
    return _mentions_compl.findall(source)


def css_link(names):
    if isinstance(names, str):
        names = names,

    for style in names:
        # FIXME MINIFY IN PREPARE
        path = consts.ASSETS / (style + '.min.css')
        # TODO: revision? Not sure, stat is easier.
        modified = (consts.L_PUBLIC / path).stat().st_mtime
        yield '{!s}?{:x}'.format(PurePath('/') / path, int(modified))


def line_breaks(value, m=2):
    pat = r'\n{{{0},}}'.format(m)
    return re.sub(pat, '\n\n', value)


_url_re = re.compile(r'((?:[\w\d]+\:\/\/)?(?:[\w\-\d]+\.)+[\w\-\d]+'
                      '(?:\/[\w\-\d]+)*(?:\/|\.[\w\-\d]+)?(?:\?[\w\-\d]+'
                      '\=[\w\-\d]+\&?)?(?:\#[\w\-\d]*)?)')
def getall_urls(text):
    getall = _url_re.findall(text)
    return set(getall)
    

def urls(value, esc=True):
    value = escape(value, quote=True) if esc else value
    urls = getall_urls(value)
    full = {}
    if urls:
        for url in urls:
            full[url] = "<a href='http://{0}' target='_blank'>{1}</a>".format(
                                            re.sub(r'^.*://', '', url),
                                            url
                                        )
        for each in full:
            value = value.replace(each, full[each])
    return value


def email_format(value):
    return bool(re.search(r'^.*?\@.*?\..*?$', value))


def name_format(value):
    return not any([
            len(value) < consts.USR_LENGTH[0],
            len(value) > consts.USR_LENGTH[1],
            frozenset(value) - consts.NAME_CHARACTERS
        ])
    

def full_date(ts):
    return datetime.fromtimestamp(ts).strftime('%I:%M %p - %b %d %Y EST (?)')


def short_date(ts):
    return datetime.fromtimestamp(ts).strftime('%d %b %Y EST(?)')


def time_passed(string, difference):
    return '{count:#d} {name}{s} ago'.format(count=int(difference), name=string,
                                             s='' if difference <= 1 else 's')


# FIXME
def gettime(timestamp, short=False):
    timestamp = float(timestamp)
    difference = time.time() - timestamp

    if difference < 4:
        return 'right now'

    elif difference < 60: # minute
        return str(int(difference)) + ' seconds ago'

    elif difference < 3600: # hour
        return time_passed('minute', difference/60 )

    elif difference < 86400: # day
        return time_passed('hour', difference/60/60 )

    elif difference < 2626560: # month
        if short: 
            return short_date(timestamp)
        else: 
            return full_date(timestamp)

    elif difference < 31518720: # year
        if short: 
            return short_date(timestamp)
        else: 
            return full_date(timestamp)

    elif difference < 315187200: # ten years
        if short: 
            return short_date(timestamp)
        else: 
            return full_date(timestamp)

    else:
        return 'Far, far ago'


def unique_hash(bits=512):
    algo = getattr(hashlib, 'sha3_' + str(bits))()
    ssl.RAND_add(uuid.uuid4().bytes, 0.0)
    for x in range(5):
        algo.update(ssl.RAND_bytes(50))
    return algo.hexdigest()


def _to_base(dec, table):
    # Convert the decimal value `dec` to len(`table`) base using `table`
    # conversion table
    b = []
    base = len(table)
    div = dec
    while div > 1:
        div, mod = divmod(div, base)
        b.append(table[mod])

    b.reverse()
    return ''.join(str(x) for x in b)


def _split_bits(value, n):
    ''' Split `value` into a list of `n`-bit integers '''
    mask, parts = (1 << n) - 1, []
    while value:
        yield value & mask
        value >>= n


def unique_id(t=consts.BASE_CONVERSION_TABLE):
    # Create `bits` bit hash and convert it to int
    uni = unique_hash(512)
    unint = int(uni, 16)
    # Create 128 bit UUID integer
    result = uuid.uuid4().int
    # Split unint into 4 128-bit integers and XOR them with result
    for i in _split_bits(unint, 128):
        result ^= i
    return _to_base(result, table=t), uni
