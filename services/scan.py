from services.abstract import AbstractService
from services.scanbusiness import ScanBusiness
from utils import response
from modles.swap import Swap
from modles import process
from modles import db
import logging


class ScanService(AbstractService):

    def __init__(self, app, rpcmanager, settings):
        AbstractService.__init__(self, app, rpcmanager, settings)
        self.businesses = {}

    def on_address_change(self, coin):
        try:
            self.businesses[coin].on_address_change()
        except Exception as e:
            logging.error('on address change failed,%s' % e)

    def start_service(self):
        AbstractService.start_service(self)

        self.businesses = ScanBusiness(self, self.rpcmanager, self.settings)
        self.businesses.start()



    def stop(self):
        AbstractService.stop(self)

