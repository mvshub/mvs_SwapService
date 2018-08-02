from services.iserver import IService
from services.swap import SwapService
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
from sqlalchemy import or_,case
import json


class MainService(IService):

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

        @self.app.route('/date/<date>')
        def swap_date(date):
            results = db.session.query(Result).filter_by(
                date=date).all()

            records = []
            for r in results:
                record = {}
                record['swap_id'] = r.swap_id
                record['coin'] = r.coin
                record['token'] = r.token
                record['tx_from'] = r.tx_from
                record['from'] = r.from_address
                record['to'] = r.to_address
                record['amount'] = r.amount
                record['time'] = "%d:%d:%d" % (r.time//10000, r.time//100%100, r.time%100)
                record['tx_height'] = r.tx_height
                record['message'] = constants.ProcessStr(
                    r.status, r.confirm_status)
                record['finish'] = 0 if r.status == int(
                    Status.Swap_Finish) else 1
                records.append(record)

            return render_template('date.html', date=date, results=records)

        @self.app.route('/<token>')
        def swap_token(token):
            results = db.session.query(Result).filter_by(
                 token=token, status=int(Status.Swap_Finish)).all()

            for result in results:
                result.time = "%d:%d:%d" % (result.time//10000, result.time//100%100, result.time%100)
                
            return render_template('token.html', token=token, results=results)

        @self.app.route('/report/<date>')
        def swap_report(date):
            finished = case([(Result.status == int(Status.Swap_Finish), 1)], else_=0)
            unfinished = case([(Result.status != int(Status.Swap_Finish), 1)], else_=0)
            results = db.session.query(
                Result.coin,
                Result.token,
                func.sum(Result.amount),
                func.sum(finished),\
                func.sum(unfinished)).\
                group_by(Result.coin, Result.token, Result.date).\
                having(Result.date == date).all()
            
            return render_template('report.html', date=date, reports=results)

        @self.app.route('/tx/<tx_from>')
        def swap_raw(tx_from):
            results = db.session.query(Result).filter_by(tx_from=tx_from).all()

            for result in results:
                result.confirm_status = constants.ConfirmStr[
                    result.confirm_status]
                result.time = "%d:%d:%d" % (result.time//10000, result.time//100%100, result.time%100)

                result.status = constants.StatusStr[result.status]

            return render_template('transaction.html', tx_from=tx_from,  results=results)

        @self.app.route('/address/<address>')
        def swap_address(address):
            results = db.session.query(Result).filter(
                or_(Result.from_address == address, Result.to_address == address)).all()
            records = []
            for r in results:
                record = {}
                record['swap_id'] = r.swap_id
                record['coin'] = r.coin
                record['token'] = r.token
                record['tx_from'] = r.tx_from
                record['from'] = r.from_address
                record['to'] = r.to_address
                record['amount'] = r.amount
                record['date'] = r.date
                record['time'] = "%d:%d:%d" % (r.time//10000, r.time//100%100, r.time%100)
                record['tx_height'] = r.tx_height
                record['message'] = constants.ProcessStr(
                    r.status, r.confirm_status)
                record['finish'] = 0 if r.status == int(
                    Status.Swap_Finish) else 1
                records.append(record)

            return render_template('address.html', address=address, results=records)

        # start swap service
        self.setup_db()
        self.rpcmanager.start()

        self.swap = SwapService(
            self.app, self.rpcmanager, self.settings['scans'])
        self.swap.start()

        # start wsgi server
        self.http = WSGIServer(
            (self.settings['host'], self.settings['port']), self.app.wsgi_app)
        Logger.get().info('server %s:%s' %
                          (self.settings['host'], self.settings['port']))
        self.http.serve_forever()

    def stop(self):
        if hasattr(self, 'http'):
            self.http.stop()

        if hasattr(self, 'swap'):
            self.swap.stop()
