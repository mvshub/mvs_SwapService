import threading


class IService:

    def __init__(self, settings):
        self.settings = settings
        self.stopped = True

    def spawn(self, f):
        threading.Thread(target=f).start()

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()
