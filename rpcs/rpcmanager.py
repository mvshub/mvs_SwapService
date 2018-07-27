import collections
import importlib
import logging
from utils.exception import RpcException, CriticalException
import random


class RpcManager:

    def __init__(self, settings):
        self.settings = settings
        self.__id_feeds = collections.defaultdict(list)
        self.__generators = {}

    def __create_generator(self, setting):
        while True:
            feed_type = setting['type']
            iden = setting['id']

            idx = feed_type.rfind('.')
            pack, cls = feed_type[:idx], feed_type[idx + 1:]
            feed_ = getattr(importlib.import_module(pack), cls)(setting)

            yield feed_

    def __create_feeds(self):
        for setting in self.settings:
            if 'id' not in setting:
                raise CriticalException('bad config, not id field found')
            id_ = setting['id']
            self.__generators[id_] = self.__create_generator(setting)

    def get_new_feed_by_id(self, id_):
        if id_ not in self.__generators:
            raise CriticalException('id %s not in the manager' % id_)
        feed_ = next(self.__generators[id_])
        feed_.start()
        self.__id_feeds[id_].append(feed_)
        return feed_

    def get_available_feed(self, id_):
        if id_ not in self.__generators:
            raise CriticalException('id %s not in the manager', id_)
        if id_ not in self.__id_feeds:
            feed_ = self.get_new_feed_by_id(id_)
        l = len(self.__id_feeds[id_])
        idx = random.randint(0, l - 1)
        return self.__id_feeds[id_][idx]

    def start(self):
        self.__create_feeds()

    def stop(self):
        self.__generators.clear()
        for id_ in self.__id_feeds:
            def do_stop(x):
                x.stop()
            filter(do_stop, self.__id_feeds[id_])
        self.__id_feeds.clear()
