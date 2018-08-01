from services.iserver import IService
from services.scan import ScanService
from rpcs.rpcmanager import RpcManager
from models import db
from models.result import Result
from models import constants
from models.constants import Status, Error, SwapException
from utils import response
from utils.log.logger import Logger
from flask import Flask, jsonify
import sqlalchemy_utils
from gevent.pywsgi import WSGIServer
from gevent import monkey
from decimal import Decimal

from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, DateTimeField, BooleanField, HiddenField, SubmitField, PasswordField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Required, Length, Email, Regexp, EqualTo
from sqlalchemy.sql import func
import json

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
        self.app.config.from_object('config.config')

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

        @self.app.route('/date/<date>')
        def swap_date(date):
            results = db.session.query(Result).filter_by(
                confirm_date=date, status=4).all()
            for result in results:
                result.amount = Decimal(result.amount).quantize(Decimal('0'))
            return render_template('swap.html', date=date, results=results)

        @self.app.route('/<coin>/<token>')
        def swap_coin(coin, token):
            results = db.session.query(Result).filter_by(
                coin=coin, token=token, status=4).all()
            for result in results:
                result.amount = Decimal(result.amount).quantize(Decimal('0'))
            return render_template('swap.html', token=token, results=results)

        @self.app.route('/report/<date>')
        def swap_report(date):
            results = db.session.query(
                Result.coin,
                Result.token,
                func.sum(Result.amount),
                func.count(1)).group_by(Result.coin, Result.token, Result.status).having(Result.status == 4).all()

            for result in results:
                result.amount = Decimal(result.amount).quantize(Decimal('0'))

            return render_template('report.html', date=date, reports=results)

        @self.app.route('/tx/<tx_raw>')
        def swap_raw(tx_raw):
            results = db.session.query(Result).filter_by(tx_raw=tx_raw).all()
            
            for result in results:
                result.amount = Decimal(result.amount).quantize(Decimal('0'))
                result.confirm_status = constants.ConfirmStr[result.confirm_status]
                result.status = constants.StatusStr[result.status]

            return render_template('transaction.html',tx_raw =tx_raw,  results=results)
 

        self.http = WSGIServer(
            (self.settings['host'], self.settings['port']), self.app.wsgi_app)
        Logger.get().info('server %s:%s' %
                          (self.settings['host'], self.settings['port']))
        self.http.serve_forever()

    def stop(self):
        if hasattr(self, 'http'):
            self.http.stop()

        if hasattr(self, 'scan'):
            self.scan.stop()
