from services.iserver import IService
from services.scan import ScanService
from rpcs.rpcmanager import RpcManager
from utils import response
from flask import Flask, jsonify
import sqlalchemy_utils
from models import db
from gevent.pywsgi import WSGIServer
from gevent import monkey
import logging


# need to patch sockets to make requests async
monkey.patch_all()


class SwapService(IService):

    def __init__(self, settings):
        self.app = None
        self.settings = settings
        self.rpcmanager = RpcManager(settings['rpcs'])

    def setup_db(self):
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://%s:%s@%s:%s/%s' % (
            self.settings['mysql_user'],
            self.settings['mysql_passwd'],
            self.settings['mysql_host'],
            self.settings['mysql_port'],
            self.settings['mysql_db'])
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
        self.app.config['extend_existing'] = True

        db.init_app(self.app)
        with self.app.app_context():
            db.create_all()

    def start(self):
        self.app = Flask(__name__)


        @self.app.route('/')
        def root():
            return response.make_response(response.ERR_SUCCESS, 'SwapService')

        @self.app.errorhandler(404)
        def not_found(error):
            return response.make_response(response.ERR_SERVER_ERROR, '404: SwapService page not found')


        self.setup_db()
        self.rpcmanager.start()

        self.scan = ScanService(
            self.app, self.rpcmanager, self.settings['scans'])
        self.scan.start()

        self.http = WSGIServer(
            (self.settings['host'], self.settings['port']), self.app.wsgi_app)
        logging.info('server %s,%s' %
                     (self.settings['host'], self.settings['port']))
        self.http.serve_forever()

    def stop(self):
        if hasattr(self, 'http'):
            self.http.stop()

        if hasattr(self, 'scan'):
            self.scan.stop()
