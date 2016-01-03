import io
import math
from PIL import Image as BaseImage, ImageOps
import urllib.error
import urllib.parse
import urllib.request
import functools

from .. import consts
from .misc import utils, abc
from .accounts import records
from fused import fields
import jinja2


class Image(abc.Item):

    _allowed = {'JPEG', 'PNG'}
    type = consts.CONTENT_IMAGE
    owner = fields.Foreign(records.Record, required=True)
    name = fields.String(required=True)

    def __init__(self, load_file=False, **ka):
        super().__init__(**ka)
        if load_file:
            self.file = self._load_file(self.name)

    @classmethod
    def _load_file(cls, name):
        # Check if we can skip loading the file from disk
        if not isinstance(name, io.IOBase):
            full_name = '{0}-{1}'.format(consts.ORIGINAL_IMAGE, name)
            name = (consts.MEDIA_IMAGES / full_name).open('rb')

        with name:
            # Same here, don't modify the original object
            with utils.keep_file_position(name):
                content = name.read()
            return BaseImage.open(io.BytesIO(content))

    @staticmethod
    def _download_file(url):
        if not urllib.parse.urlparse(url)[0]:
            url = 'http://{}'.format(url)

        return io.BytesIO(urllib.request.urlopen(url, timeout=10).read())

    def setavatar(self):
        ''' `Image.setavatar` (as well as `Image.setcover`) performs only file IO 
            operations. No database stuff.'''
        path = consts.MEDIA_IMAGES / '{0}-{1}'.format(consts.AVATAR , self.name)
        if not path.exists():
            new = ImageOps.fit(self.file, (500, 500), BaseImage.ANTIALIAS)
            new.save(str(path), quality=100)

    def setcover(self):
        path = consts.MEDIA_IMAGES / '{0}-{1}'.format(consts.COVER_IMAGE , self.name)
        if not path.exists():
            ratio = consts.COVER_RATIO[1] / consts.COVER_RATIO[0]
            nh = math.ceil(self.file.size[0] * ratio)
            cr = ImageOps.fit(self.file, (self.file.size[0], nh), BaseImage.ANTIALIAS)
            cr.save(str(path), quality=100)

    @classmethod
    def _store(cls, acct, file, allow_gif):
        # `file` argument must be provided
        with utils.keep_file_position(file):
            content = file.read()
        if len(content) > consts.MAX_IMAGE_SIZE:
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
        names = [consts.MEDIA_IMAGES / '{}-{}'.format(x, name) for x in sizes]

        consts.MEDIA_IMAGES.mkdir(parents=True, exist_ok=True)
        
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

        return name

    def delete(self):
        name = self.name
        super().delete()
        for file in consts.MEDIA_IMAGES.glob('*-' + name):
            file.unlink()
            
        # acct.delete_images(images)

    @classmethod
    def new(cls, acct, image, allow_gif=False):        
        if not isinstance(acct, records.Record):
            raise TypeError

        if isinstance(image, str):
            # _download_file doesn't track exceptions
            image = cls._download_file(image)
        
        name = cls._store(acct, image, allow_gif)
        new = super().new(owner=acct.id, name=name)
        # acct.add_image(new)
        return new
                

def urls_dict(name, types=()):
    func = functools.partial(utils.image_url, name=name)
    return {x: func(type=x) for x in types}