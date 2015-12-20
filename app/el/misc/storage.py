from ... import consts
from redis import Redis


def get_main_connection():
    return Redis.from_url(consts.ext.REDIS_MAIN_URL)


def get_feed_connection():
    return Redis.from_url(consts.ext.REDIS_FEED_URL)
