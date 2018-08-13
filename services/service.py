from services.iserver import IService
from services.swap import SwapService
from rpcs.rpcmanager import RpcManager
from models import db
from models.result import Result
from models import constants
from models.constants import Status, Error, SwapException
from utils import response
from utils.log.logger import Logger
from flask import Flask, jsonify, redirect, url_for
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
from sqlalchemy import or_, and_, case
import json
import re

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
            return render_template('index.html')

        @self.app.route('/getResult')
        def getResult():
            results = db.session.query(Result).order_by(
            Result.swap_id.desc()).limit(1000).all()
            records = []
            for r in results:
                record = {}
                record['swap_id'] = r.swap_id
                record['coin'] = r.coin
                record['token'] = r.token
                record['tx_from'] = r.tx_from
                record['from'] = r.from_address
                record['to'] = r.to_address
                record['amount'] = self.format_amount(r.amount)
                record['fee'] = self.format_amount(r.fee)
                record['date'] = r.date
                record['time'] = "%02d:%02d:%02d" % (
                    r.time // 10000, r.time // 100 % 100, r.time % 100)
                record['tx_height'] = r.tx_height
                record['message'] = constants.ProcessStr(
                    r.status, r.confirm_status)
                record['finish'] = 0 if r.status == int(
                    Status.Swap_Finish) else 1
                records.append(record)

            return json.dumps(records)

        @self.app.route('/query', methods=['GET','POST'])
        def query():
            #import pdb; pdb.set_trace()
            from wtforms import StringField, SubmitField
            from wtforms.validators import Required
            class MockCreate(FlaskForm):
                submit = SubmitField("Submit")
                condition = StringField("condition", [Required()])
            form = MockCreate()
            condition = form['condition'].data
            #print (condition)

            def isBase58(addr):
                pattern = '^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{34}$'
                m = re.match(pattern, addr)
                return m != None

            def isBase16(addr):
                pattern = '^(0x)?([0-9a-f]+)$'
                m = re.match(pattern, addr.lower())
                if not m:
                    return False
                return len(m.groups()[1]) == 40
            if isBase58(condition) or isBase16(condition):
                return redirect(url_for('swap_address', address=condition))

            def isDate(date):
                pattern = '^\d{8}$'
                m = re.match(pattern, date)
                if not m:
                    return False
                year = date[:4]
                month = date[4:6]
                day = date[6:]
                return '2018' <= year <= '2030' and '01' <= month <= '12' and '01' <= day <= '31'

            if isDate(condition):
                return redirect(url_for('swap_date', date=condition))

            def isMvsTxHash(txhash):
                pattern = '^[0-9a-f]{64}$'
                m = re.match(pattern, txhash)
                return m != None

            def isEthTxHash(txhash):
                pattern = '^0x[0-9a-f]{64}$'
                m = re.match(pattern, txhash)
                return m != None

            if isMvsTxHash(condition) or isEthTxHash(condition):
                return redirect(url_for('swap_raw', tx_from=condition))

        @self.app.errorhandler(404)
        def not_found(error):
            return response.make_response(response.ERR_SERVER_ERROR, '404: SwapService page not found')

        @self.app.route('/status/<coin>/<token>/<date>/<int:status>')
        def swap_status(coin, token, date, status=0):

            if status == 0:
                results = db.session.query(Result).filter_by(
                    date=date, coin=coin, token=token).order_by(Result.swap_id.desc()).all()
            elif status == 1:
                results = db.session.query(Result).filter_by(
                    date=date, coin=coin, token=token, status=int(Status.Swap_Finish)).order_by(Result.swap_id.desc()).all()
            else:
                results = db.session.query(Result).filter(and_(
                    Result.date == date, Result.coin == coin, Result.token == token,
                    Result.status != int(Status.Swap_Finish))).order_by(Result.swap_id.desc()).all()

            records = []
            for r in results:
                record = {}
                record['swap_id'] = r.swap_id
                record['coin'] = r.coin
                record['token'] = r.token
                record['tx_from'] = r.tx_from
                record['from'] = r.from_address
                record['to'] = r.to_address
                record['amount'] = self.format_amount(r.amount)
                record['fee'] = self.format_amount(r.fee)
                record['time'] = "%02d:%02d:%02d" % (
                    r.time // 10000, r.time // 100 % 100, r.time % 100)
                record['tx_height'] = r.tx_height
                record['message'] = constants.ProcessStr(
                    r.status, r.confirm_status)
                record['finish'] = 0 if r.status == int(
                    Status.Swap_Finish) else 1
                records.append(record)

            return render_template('date.html', date=date, results=records)

        @self.app.route('/date/<date>')
        def swap_date(date):
            results = db.session.query(Result).filter_by(
                date=date).order_by(Result.swap_id.desc()).all()
            records = []
            for r in results:
                record = {}
                record['swap_id'] = r.swap_id
                record['coin'] = r.coin
                record['token'] = r.token
                record['tx_from'] = r.tx_from
                record['from'] = r.from_address
                record['to'] = r.to_address
                record['amount'] = self.format_amount(r.amount)
                record['fee'] = self.format_amount(r.fee)
                record['time'] = "%02d:%02d:%02d" % (
                    r.time // 10000, r.time // 100 % 100, r.time % 100)
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
                token=token).order_by(Result.swap_id.desc()).all()

            for result in results:
                result.time = "%02d:%02d:%02d" % (
                    result.time // 10000, result.time // 100 % 100, result.time % 100)
                result.amount = self.format_amount(result.amount)
                result.fee = self.format_amount(result.fee)

            return render_template('token.html', token=token, results=results)

        @self.app.route('/report/<date>')
        def report_per_day(date):
            num_finished = case(
                [(Result.status == int(Status.Swap_Finish), 1)], else_=0)
            total_finished = case(
                [(Result.status == int(Status.Swap_Finish), Result.amount)], else_=0)
            num_pending = case(
                [(Result.status != int(Status.Swap_Finish), 1)], else_=0)
            total_pending = case(
                [(Result.status != int(Status.Swap_Finish), Result.amount)], else_=0)
            num_total = case([(Result.date == date, 1)], else_=0)
            total = case([(Result.date == date, Result.amount)], else_=0)
            total_fee = case([(Result.date == date, Result.fee)], else_=0)

            results = db.session.query(
                Result.coin,
                Result.token,
                func.sum(num_finished),
                func.sum(total_finished),
                func.sum(num_pending),
                func.sum(total_pending),
                func.sum(num_total),
                func.sum(total),
                func.sum(total_fee)).\
                group_by(Result.coin, Result.token, Result.date).\
                having(Result.date == date).all()

            results = [(x[0], x[1],
                        x[2], self.format_rough_amount(x[3]),
                        x[4], self.format_rough_amount(x[5]),
                        x[6], self.format_rough_amount(x[7]),
                        self.format_rough_amount(x[8])) for x in results]
            return render_template('reportperday.html', date=date, reports=results)

        @self.app.route('/report/<date1>/<date2>')
        def report_between(date1, date2):
            finished = case(
                [(Result.status == int(Status.Swap_Finish), 1)], else_=0)
            total_amount = case(
                [(Result.status == int(Status.Swap_Finish), Result.amount)], else_=0)
            total_fee = case(
                [(Result.status == int(Status.Swap_Finish), Result.fee)], else_=0)
            pending = case(
                [(Result.status != int(Status.Swap_Finish), 1)], else_=0)
            total_pending = case(
                [(Result.status != int(Status.Swap_Finish), Result.amount)], else_=0)

            results = db.session.query(
                Result.coin,
                Result.token,
                func.sum(total_amount),
                func.sum(total_fee),
                func.sum(finished),
                func.sum(total_pending),
                func.sum(pending)). \
                filter(and_(Result.date <= date2, Result.date >= date1)). \
                group_by(Result.coin, Result.token).all()

            results = [(x[0], x[1],
                        self.format_rough_amount(x[2]),
                        self.format_rough_amount(x[3]),
                        x[4], self.format_rough_amount(x[5]), x[6]) for x in results]
            return render_template('report.html', date="%s -- %s" % (date1, date2), reports=results)

        @self.app.route('/tx/<tx_from>')
        def swap_raw(tx_from):
            results = db.session.query(Result).filter_by(tx_from=tx_from).all()

            for result in results:
                result.confirm_status = constants.ConfirmStr[
                    result.confirm_status]
                result.time = "%02d:%02d:%02d" % (
                    result.time // 10000, result.time // 100 % 100, result.time % 100)
                result.amount = self.format_amount(result.amount)
                result.fee = self.format_amount(result.fee)
                result.status = constants.StatusStr[result.status]

            return render_template('transaction.html', tx_from=tx_from,  results=results)

        @self.app.route('/address/<address>')
        def swap_address(address):
            results = db.session.query(Result).filter(
                or_(Result.from_address == address, Result.to_address == address)).order_by(Result.swap_id.desc()).all()
            records = []
            for r in results:
                record = {}
                record['swap_id'] = r.swap_id
                record['coin'] = r.coin
                record['token'] = r.token
                record['tx_from'] = r.tx_from
                record['from'] = r.from_address
                record['to'] = r.to_address
                record['amount'] = self.format_amount(r.amount)
                record['fee'] = self.format_amount(r.fee)
                record['date'] = r.date
                record['time'] = "%02d:%02d:%02d" % (
                    r.time // 10000, r.time // 100 % 100, r.time % 100)
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

    def format_amount(self, amount):
        if not amount:
            return '0'

        amount_str = str(amount)
        if amount_str.find('.') != -1:
            amount_str = amount_str.rstrip('0')
            if amount_str.endswith('.'):
                amount_str = amount_str[0:len(amount_str) - 1]
        if amount_str == '0E-18':
            amount_str = '0'
        return amount_str

    def format_rough_amount(self, amount):
        if not amount:
            return '0'

        amount_str = '{:0.4f}'.format(float(amount))
        if amount_str.find('.') != -1:
            amount_str = amount_str.rstrip('0')
            if amount_str.endswith('.'):
                amount_str = amount_str[0:len(amount_str) - 1]
        if amount_str == '0E-18':
            amount_str = '0'
        return amount_str
