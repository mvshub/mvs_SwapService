from services.iserver import IService
from services.swap import SwapService
from rpcs.rpcmanager import RpcManager
from models import db
from models.result import Result
from models.binder import Binder
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
import time
import codecs


class MainService(IService):

    def __init__(self, settings):
        self.app = None
        self.settings = settings
        self.rpcmanager = RpcManager(settings['rpcs'], settings['tokens'])

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

        import os
        self.app.config['CSRF_ENABLED'] = True
        self.app.config['SECRET_KEY'] = os.urandom(24)
        
        @self.app.route('/')
        def root():
            return render_template('index.html')

        @self.app.route('/query', methods=['GET', 'POST'])
        def query():
            class FormCondition(FlaskForm):
                submit = SubmitField("Submit")
                condition = StringField("condition", [Required()])
            form = FormCondition()
            condition = form['condition'].data
            #print (condition)

            if condition.isdigit():
                result = db.session.query(Result).filter_by(
                    swap_id=condition).limit(1).first()
                if result:
                    return redirect(url_for('swap_raw', tx_from=result.tx_from))

                result = db.session.query(Result).filter_by(
                    date=condition).limit(1).first()
                if result:
                    return redirect(url_for('swap_date', date=condition))

            result = db.session.query(Result).filter(
                or_(Result.from_address == str(condition),
                    Result.to_address == str(condition))).limit(1).first()
            if result:
                return redirect(url_for('swap_address', address=condition))

            result = db.session.query(Result).filter_by(
                tx_from=str(condition)).limit(1).first()
            if result:
                return redirect(url_for('swap_raw', tx_from=condition))

            result = db.session.query(Result).filter_by(
                token=str(condition)).limit(1).first()
            if result:
                return redirect(url_for('swap_token', token=condition))

            return response.make_response(response.ERR_BAD_PARAMETER)

        @self.app.route('/getResult')
        def getResult():
            results = db.session.query(Result).order_by(
                Result.swap_id.desc()).limit(1000).all()
            records = []

            def getMinconf(coin, token):
                if coin == 'ETH' or coin == 'ETHToken':
                    coin = 'ETP'
                elif coin == 'ETP' and token == (constants.SWAP_TOKEN_PREFIX + 'ETH'):
                    coin = 'ETH'
                else:
                    coin = 'ETHToken'

                for c in self.settings['scans']['services']:
                    if c['coin'] == coin:
                        return c['minconf']
                return 0

            for r in results:
                record = {}
                record['swap_id'] = r.swap_id
                record['coin'] = r.coin
                record['token'] = r.token
                record['tx_from'] = r.tx_from
                record['from'] = r.from_address
                record['to'] = r.to_address
                record['amount'] = self.format_amount(r.amount)
                record['fee'] = self.format_amount(r.from_fee)
                record['date'] = r.date
                record['time'] = self.format_time(r.time)
                record['tx_height'] = r.tx_height
                record['confirm_height'] = r.confirm_height
                record['message'] = constants.ProcessStr(
                    r.status, r.confirm_status)
                record['finish'] = 0 if r.status == int(
                    Status.Swap_Finish) else 1
                record['minconf'] = getMinconf(r.coin, r.token)
                records.append(record)

            return json.dumps(records)

        @self.app.errorhandler(404)
        def not_found(error):
            return response.make_response(response.ERR_SERVER_ERROR, '404: SwapService page not found')

        @self.app.route('/status/<coin>/<token>/<date>/<int:status>')
        def swap_status(coin, token, date, status=0):

            if status == 0:
                results = db.session.query(Result).filter_by(
                    date=date, coin=coin, token=token).order_by(
                    Result.swap_id.desc()).all()
            elif status == 1:
                results = db.session.query(Result).filter_by(
                    date=date, coin=coin, token=token, status=int(Status.Swap_Finish)).order_by(
                    Result.swap_id.desc()).all()
            else:
                results = db.session.query(Result).filter(and_(
                    Result.date == date, Result.coin == coin, Result.token == token,
                    Result.status != int(Status.Swap_Finish))).order_by(
                    Result.swap_id.desc()).all()

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
                record['fee'] = self.format_amount(r.from_fee)
                record['time'] = self.format_time(r.time)
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
                record['fee'] = self.format_amount(r.from_fee)
                record['time'] = self.format_time(r.time)
                record['tx_height'] = r.tx_height
                record['message'] = constants.ProcessStr(
                    r.status, r.confirm_status)
                record['finish'] = 0 if r.status == int(
                    Status.Swap_Finish) else 1
                records.append(record)

            return render_template('date.html', date=date, results=records)

        @self.app.route('/token/<token>')
        def swap_token(token):
            results = db.session.query(Result).filter_by(
                token=token).order_by(Result.swap_id.desc()).all()

            for result in results:
                result.time = self.format_time(result.time)
                result.amount = self.format_amount(result.amount)
                result.fee = self.format_amount(result.from_fee)

            return render_template('token.html', token=token, results=results)

        @self.app.route('/report/<date>')
        @self.app.route('/report')
        def report_per_day(date=None):
            if not date:
                date = time.strftime('%4Y%2m%2d', time.localtime())

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
            total_fee = case([(Result.date == date, Result.from_fee)], else_=0)

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
                [(Result.status == int(Status.Swap_Finish), Result.from_fee)], else_=0)
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

        @self.app.route('/report_query', methods=['GET', 'POST'])
        def report_query():
            class FormQuery(FlaskForm):
                submit = SubmitField("Submit")
                date_from = StringField("date_from", [Required()])
                date_to = StringField("date_to")
            form = FormQuery()
            date_from = form['date_from'].data
            date_to = form['date_to'].data
            if date_to:
                return redirect(url_for('report_between', date1=date_from, date2=date_to))
            else:
                return redirect(url_for('report_per_day', date=date_from))

        @self.app.route('/tx/<tx_from>')
        def swap_raw(tx_from):
            result = db.session.query(Result).filter_by(
                tx_from=tx_from).first()

            if result != None:
                result.confirm_status = constants.ConfirmStr[
                    result.confirm_status]
                result.time = self.format_time(result.time)
                result.amount = self.format_amount(result.amount)
                result.fee = self.format_amount(result.from_fee)
                result.status = constants.StatusStr[result.status]
                return render_template('transaction.html', tx_from=tx_from,  result=result)
            else:
                return response.make_response(response.ERR_INVALID_TRANSACTION)

        @self.app.route('/address/<address>')
        def swap_address(address):
            results = db.session.query(Result).filter(
                or_(Result.from_address == address, Result.to_address == address)).order_by(
                Result.swap_id.desc()).all()
            records = []
            binders = []
            for r in results:
                record = {}
                record['swap_id'] = r.swap_id
                record['coin'] = r.coin
                record['token'] = r.token
                record['tx_from'] = r.tx_from
                record['from'] = r.from_address
                record['to'] = r.to_address
                record['amount'] = self.format_amount(r.amount)
                record['fee'] = self.format_amount(r.from_fee)
                record['date'] = r.date
                record['time'] = self.format_time(r.time)
                record['tx_height'] = r.tx_height
                record['message'] = constants.ProcessStr(
                    r.status, r.confirm_status)
                record['finish'] = 0 if r.status == int(
                    Status.Swap_Finish) else 1
                records.append(record)

            results = db.session.query(Binder).filter_by(
                binder=address).order_by(Binder.iden.desc()).all()
            for r in results:
                bind = {}
                bind['from'] = r.binder
                bind['to'] = r.to
                bind['height'] = r.block_height
                binders.append(bind)

            return render_template('address.html', address=address, results=records, binders=binders)

        @self.app.route('/swapcode/<address>')
        def swap_code(address):
            func_prototype = '0xfa42f3e5'
            nonfix_distance = '0000000000000000000000000000000000000000000000000000000000000020'

            len_of_address = len(address)
            len_encoded = "{:064x}".format(len_of_address)

            address_encoded = codecs.encode(address.encode(), 'hex').decode()
            len_padding = len(address_encoded) % 64
            if len_padding != 0:
                len_padding = 64 - len_padding
                address_encoded = address_encoded + ('0' * len_padding)

            result = {}
            rpcs = self.settings['rpcs']
            contract_mapaddress = ''
            for x in rpcs:
                if 'name' in x and x['name'] == 'ETHToken':
                    contract_mapaddress = x['contract_mapaddress']
                    break
            result['did_or_address'] = address
            result['contract_mapaddress'] = contract_mapaddress
            result['swapcode'] = func_prototype + \
                nonfix_distance + len_encoded + address_encoded
            return json.dumps(result, indent=4)

        @self.app.route('/ban/<date>')
        @self.app.route('/ban')
        def swap_ban(date=None):
            if not date:
                date = time.strftime('%4Y%2m%2d', time.localtime())
            return render_template('ban.html', date=date)

        @self.app.route('/getBan/<date>')
        def getBan(date):
            results = db.session.query(Result).filter(and_(
                Result.date == int(date),
                Result.status == int(Status.Swap_Ban))).order_by(Result.swap_id.desc()).all()

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
                record['fee'] = self.format_amount(r.from_fee)
                record['time'] = self.format_time(r.time)
                record['message'] = r.message

                if r.coin == 'ETH' or r.coin == 'ETHToken':
                    if len(r.to_address) == 34:
                        record[
                            'scan'] = 'https://explorer.mvs.org/adr/' + r.to_address
                    else:
                        record[
                            'scan'] = 'https://explorer.mvs.org/avatar/' + r.to_address
                elif r.coin == 'ETP':
                    record['scan'] = 'https://etherscan.io/address/' + \
                        r.to_address

                records.append(record)

            return json.dumps(records)

        @self.app.route('/retry', methods=['POST'])
        def swap_retry():
            swap_id = request.form.get('swap_id')
            result = db.session.query(Result).filter_by(
                swap_id=swap_id).first()
            if result:
                result.status = int(Status.Swap_New)
                result.message = "Retry swap"
                result.date = int(time.strftime('%4Y%2m%2d', time.localtime()))
                result.time = int(time.strftime('%2H%2M%2S', time.localtime()))
                db.session.add(result)
                db.session.commit()
                return response.make_response(
                    response.ERR_SUCCESS,
                    "retry success,swap_id: %d, coin: %s , token: %s, from: %s, to: %s, amount: %f" % (
                        result.swap_id, result.coin, result.token, result.from_address,
                        result.to_address, result.amount))

            return response.make_response(response.ERR_INVALID_SWAPID)

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
        return self.format_amount_str(amount_str)

    def format_rough_amount(self, amount):
        if not amount:
            return '0'

        amount_str = '{:0.4f}'.format(float(amount))
        return self.format_amount_str(amount_str)

    def format_amount_str(self, amount_str):
        dot_index = amount_str.find('.')
        if dot_index != -1:
            e_index = amount_str.find('E-', dot_index)
            if e_index == -1:
                amount_str = amount_str.rstrip('0')
                if amount_str.endswith('.'):
                    amount_str = amount_str[0:len(amount_str) - 1]
            else:
                prefix = amount_str[:e_index]
                postfix = amount_str[e_index:]
                prefix = prefix.rstrip('0')
                if prefix.endswith('.'):
                    prefix = prefix[0:len(prefix) - 1]
                amount_str = prefix + postfix

        if amount_str == '0E-18':
            amount_str = '0'
        return amount_str

    def format_time(self, time):
        return "%02d:%02d:%02d" % (
            time // 10000, time // 100 % 100, time % 100)
