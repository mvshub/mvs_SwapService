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

        self.register_service('/service/%s/block/number',
                             self.process_get_block_number, '%s_block_number')

    def process_get_block_number(self, rpc, setting):
        self.get_best_block_number(rpc)
        return response.make_response(result=self.best_block_number)

    def get_best_block_number(self, rpc):
        self.best_block_number = rpc.best_block_number()
        return self.best_block_number

    def stop(self):
        AbstractService.stop(self)
