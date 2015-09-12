class Error(Exception):
    pass
    

class MultiError(Exception):

    def __init__(self):
        self.exc = []

    def add(self, e):
        self.exc.append(e)

    def raise_all(self):
        if self.exc:
            raise self

    def __repr__(self):
        return repr(self.exc)

    def __bool__(self):
        return bool(self.exc)

    __str__ = __repr__


class NoAuth(Error):
    description = 'You need to be authenticated to perform this action'
    def __init__(self, text='Not authenticated'):
        self.args = (text,)


class NotFound(Error):
    description = None
    def __init__(self, restype, text=None):
        if text is not None:
            self.args = (text,)
        else:
            self.args = ('The requested {} was not found'.format(restype),)


class Ambiguous(Error):
    description = None
    def __init__(self, text='Confilicting/Too many parameters'):
        self.args = (text,)


class BadValue(Error):
    description = None 
    def __init__(self, parameter):
        self.param = parameter

    def __repr__(self):
        return 'Got an unexpected value for parameter {}'.format(self.param)

    __str__ = __repr__


class NothingToUpload(Error):
    description = 'You need to provide files/URL to upload from'
    def __init__(self, text='Nothing to upload'):
        self.args = (text,)


class PartialSuccess(Error):
    description = None
    def __init__(self, succesful, total):
        self.args = succesful, total

    def __repr__(self):
        return 'Only {}/{} of items were succefully processed'.format(*self.args)

    __str__ = __repr__


class UnsupportedImageType(Error):
    description = 'The data you provided is of unsupported type'
    def __init__(self, text='Unsupported image type'):
        self.args = (text,)


class NothingToDelete(Error):
    description = None
    def __init__(self, text='Nothing to delete'):
        self.args = (text,)


class PostTooLong(Error):
    description = None
    def __init__(self, diff):
        self.args = ('Your post\'s length exceeds the maximum' 
                     'length by {} characters'.format(diff),)


class EmptyPost(Error):
    description = None
    def __init__(self, text='Your post is empty'):
        self.args = (text,)


class NothingToRate(Error):
    description = None
    def __init__(self, action):
        self.args = ('Nothing to {}'.format(action),)


class UnknownAction(Error):
    description = None
    def __init__(self, part, action):
        self.args = ('Unknown action {!r} in the {!r} part'.format(action, part),)


class NoParams(Error):
    description = None
    def __init__(self, text='You provided no parameters, the output can '
                            ' be empty'):
        self.args = (text,)

class NotEnoughParams(Error):
    description = None
    def __init__(self, text='Please provide the required parameters'):
        self.args = (text,)


class IncorrectPassword(Error):
    description = None
    def __init__(self, text='The password you provided is incorrect'):
        self.args = (text,)


class WrongFormat(Error):
    description = None
    def __init__(self, arg):
        self.args = ('The provided {} has invalid format'.format(arg),)


class Taken(Error):
    description = None
    def __init__(self, arg):
        self.args = ('The specified {} has already been taken'.format(arg),)


class NotPermitted(Error):
    description = None