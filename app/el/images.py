import io
import math
from PIL import Image as BaseImage, ImageOps
import urllib.error
import urllib.parse
import urllib.request
import functools

from .. import consts
from .misc import utils, abc
from .accounts.records import Record

import jinja2
from bson.objectid import ObjectId
from pymongo import MongoClient

client = MongoClient()


class Image(abc.Scorable, abc.Item):

    ''' Represents a single image. 
        The implementation is similar to `posts.Post`.  '''

    _allowed = {'JPEG', 'PNG'}
    type = consts.CONTENT_IMAGE
    _db, _collection = consts.MONGO['images']
    collection = client[_db][_collection]

    def __init__(self, image=None, file=False):
        ''' Getting truthy `file` requires loading the image from disc. Don't do
            that unless you're sure you need the image object. '''
        self._fields = {}
        self.derived = []
        if image:
            image = ObjectId(image)
            data = self.collection.find_one({self.pk: image}) or {}
            if data and file:
                data['file'] = self._load_file(data['name'])
            self._init_setfields(self, data)

    def _prepare(self):
        if self.owner and not isinstance(self.owner, Record):
            self._setfields(self, {'owner': Record(id=self.owner)})

    @classmethod
    def _load_file(cls, file):
        # Check if we can skip loading the file from disk
        if not isinstance(file, io.IOBase):
            full_name = '{0}-{1}'.format(consts.ORIGINAL_IMAGE, file)
            file = (consts.L_MEDIA_IMAGES / full_name).open('rb')

        with file:
            # Same here, don't modify the original object
            content = file.read()
            file.seek(0)
            return BaseImage.open(io.BytesIO(content))

    @staticmethod
    def _download(url):
        if not urllib.parse.urlparse(url)[0]:
            url = 'http://{}'.format(url)

        return io.BytesIO(urllib.request.urlopen(url, timeout=10).read())

    @classmethod
    def _store_n_link(cls, acct, file, allow_gif=False):
        # `file` argument must be provided
        content = file.read()
        # Keep the original object unmodified.
        # It won't be used anywhere in this function
        file.seek(0)

        if len(content) > consts.MAX_FILE_SIZE:
            raise ValueError('Image is too large')

        try:
            # Try to get image type
            img = BaseImage.open(io.BytesIO(content))
            if img.format not in cls._allowed.union({'GIF'} if allow_gif else set()):
                raise ValueError
        except (IOError, ValueError) as e:
            raise ValueError('Invalid image type') from None

        name = '{}.{}'.format(utils.unique_id()[0], img.format.lower())
        sizes = (consts.ORIGINAL_IMAGE, consts.SQUARE_THUMBNAIL, consts.SHRINKED_IMAGE)
        names = [consts.L_MEDIA_IMAGES / '{}-{}'.format(x, name) for x in sizes]

        # Save full image without changin' a byte
        with names[0].open('wb') as unmodified:
            unmodified.write(content)

        # Construct `PIL.Image` instance and make a thumbnail and a shrinked copy

        # Thumbnails are always square
        ImageOps.fit(img, (100, 100), BaseImage.ANTIALIAS).save(str(names[1]), quality=100)
        # Shrinked image is a fixed-width image derived from the full-size image
        # Don't modify GIF images
        if consts.SHRINKED_WIDTH < img.size[0] and img.format != 'GIF':
            nh = math.ceil(consts.SHRINKED_WIDTH / img.size[0] * img.size[1])
            shrinked = ImageOps.fit(img, (consts.SHRINKED_WIDTH, nh), BaseImage.ANTIALIAS)
            shrinked.save(str(names[2]), quality=100)
        else:
            with names[2].open('wb') as shrinked:
                shrinked.write(content)

        # Link the image to `acct`, create a new `Image` instance and return it
        data = {'name': name, 'owner': acct.id, 'id': utils.unique_id()[0], 'score': 0}
        cls.collection.insert_one(data)
        data['owner'] = acct
        data['file'] = img
        return data

    @classmethod
    def fromdata(cls, data, file=False):
        if file:
            data['file'] = cls._load_file(data['name'])
        # I think it's okay to go against DRY now
        return cls._init_setfields(cls(), data)

    def setavatar(self):
        ''' `Image.setavatar` (as well as `Image.setcover`) performs only file IO 
            operations. No database stuff.'''
        path = consts.L_MEDIA_IMAGES / '{0}-{1}'.format(consts.AVATAR , self.name)
        if not path.exists():
            new = ImageOps.fit(self.file, (500, 500), BaseImage.ANTIALIAS)
            new.save(str(path), quality=100)

    def setcover(self):
        path = consts.L_MEDIA_IMAGES / '{0}-{1}'.format(consts.COVER_IMAGE , self.name)
        if not path.exists():
            ratio = consts.COVER_RATIO[1] / consts.COVER_RATIO[0]
            nh = math.ceil(self.file.size[0] * ratio)
            cr = ImageOps.fit(self.file, (self.file.size[0], nh), BaseImage.ANTIALIAS)
            cr.save(str(path), quality=100)

    @classmethod
    def delete(cls, acct, images):
        if not isinstance(acct, Record):
            raise TypeError

        if not images:
            raise ValueError('Nothing to delete')

        ins = cls.instances(images)
        # Make a list excluding not `acct`'s images
        valid = [x for x in ins if x.owner == acct]

        for name in (x.name for x in valid):
            for file in consts.L_MEDIA_IMAGES.glob('*-' + name):
                file.unlink()

        with acct:
            op = cls.collection.delete_many({cls.pk: {'$in': [x.id for x in valid]}})
            acct.images -= op.deleted_count

    @classmethod
    def new(cls, acct, images, allow_gif=False):
        ''' `images` is an iterable of file objects or strings.
            Strings are treated as URLs '''
        
        if not isinstance(acct, Record):
            raise TypeError

        if not images:
            raise ValueError('No data supplied')

        with acct:
            for img in images:
                if isinstance(img, str):
                    # _download doesn't track exceptions
                    try:
                        img = cls._download(img)
                    except (urllib.error.URLError,) as e:
                        continue
                try:
                    data = cls._store_n_link(acct, img, allow_gif)
                except (ValueError, IOError) as e: # Invalid image
                    continue
                else:
                    acct.images += 1
                    yield cls.fromdata(data)

    def __repr__(self):
        pat = '<Image object at {addr:#x}: {self.pk}={self.id}>'
        mapping = {'addr': id(self), 'self': self}
        return pat.format(**mapping)
                

def urls_dict(name, types=()):
    func = functools.partial(utils.image_url, name=name)
    return {x: func(type=x) for x in types}


def raw(acct, number=50, files=False):
    if not isinstance(acct, Record):
        raise TypeError

    imgs = Image.collection.find({'owner': acct.id})
    # Returns instances
    fromdata = functools.partial(Image.fromdata, file=files)
    yield from map(fromdata, imgs.sort([('$natural', -1)]).limit(number))