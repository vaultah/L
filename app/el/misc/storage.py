from ... import consts
from redis import StrictRedis


def get_main_connection():
    return StrictRedis.from_url(consts.ext.REDIS_MAIN_URL, encoding='utf-8')


def get_feed_connection():
    return StrictRedis.from_url(consts.ext.REDIS_FEED_URL, encoding='utf-8')
