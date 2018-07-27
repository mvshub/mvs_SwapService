from services.abstract import AbstractService
from services.scanbusiness import ScanBusiness
from utils import response
from models.swap import Swap
from models.result import Result
from models import process
from models import db
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

        self.post(self.work_routine)

        self.businesses = ScanBusiness(self, self.rpcmanager, self.settings)
        self.businesses.start()

    def scan_swap(self):
        return db.session.query(Swap).filter( Swap.iden>0 ).all()
        #from sqlalchemy.sql import func
        #return db.session.query(func.max(Swap.iden)).all()

    def process_swap_request(self, swap):
        print ('ToDo: process_swap_request:', swap)

    def work_routine(self):
        #1. scan table swap
        swaps = self.scan_swap()
        #2. process swap request
        for swap in swaps:
            self.process_swap_request(swap)

            #3. commit swap result
        print('work_routine is running')
        return True

    def stop(self):
        AbstractService.stop(self)

