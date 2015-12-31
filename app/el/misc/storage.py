from ... import consts
from redis import StrictRedis


def get_main_connection():
    return StrictRedis.from_url(consts.ext.REDIS_MAIN_URL)


def get_feed_connection():
    return StrictRedis.from_url(consts.ext.REDIS_FEED_URL)
