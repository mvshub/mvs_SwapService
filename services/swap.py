from services.abstract import AbstractService
from services.swapbusiness import SwapBusiness
from utils import response
from models import db


class SwapService(AbstractService):

    def __init__(self, app, rpcmanager, settings):
        AbstractService.__init__(self, app, rpcmanager, settings)
        self.businesses = {}

    def start_service(self):
        AbstractService.start_service(self)

        self.businesses = SwapBusiness(self, self.rpcmanager, self.settings)
        self.businesses.start()

    def stop(self):
        AbstractService.stop(self)
