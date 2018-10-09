from services.iserver import IService
from services.swap import SwapService
from rpcs.rpcmanager import RpcManager
from models import db
from models.result import Result
from models.binder import Binder
from models import constants
from models.constants import Status, Error, SwapException
from utils import response
from utils import date_time
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
import codecs


class MainService(IService):

    def __init__(self, settings):
        self.app = None
        self.settings = settings

        self.num_per_page = int(settings.get('num_per_page',50))
        if self.num_per_page < 1:
            self.num_per_page = 1

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

    def calculate_page_index(self, total_count, page_index):
        total_page = 1
        if total_count > self.num_per_page:
            total_page, mod = divmod(total_count, self.num_per_page)
            total_page = total_page + (1 if mod != 0 else 0)

        if page_index < 1:
            page_index = 1
        elif page_index > total_page:
            page_index = total_page
        return page_index

    def paginate(self, query, page_index):
        total_count = query.count()
        page_index = self.calculate_page_index(total_count, page_index)
        results = query.paginate(
            page_index, self.num_per_page, False).items
        return page_index, results

    def parse_date(self, date_str):
        dates = date_str.split('--')
        start_date = ''
        end_date = ''
        if len(dates) == 2:
            start_date = dates[0].strip()
            end_date = dates[1].strip()
        elif len(dates) == 1:
            start_date = dates[0].strip()
            end_date = start_date
        return start_date, end_date

    def start(self):
        self.app = Flask(__name__)

        import os
        self.app.config['CSRF_ENABLED'] = True
        self.app.config['SECRET_KEY'] = os.urandom(24)

        @self.app.route('/')
        def root():
            return render_template('index.html', page_index=1)

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

        @self.app.route('/index/<int:page_index>')
        @self.app.route('/index')
        def view_index(page_index=1):
            total_count = Result.query.count()
            page_index = self.calculate_page_index(total_count, page_index)
            return render_template('index.html', page_index=page_index)


        @self.app.route('/getResult/<int:page_index>')
        def getResult(page_index=1):
            # paginate
            results = Result.query.order_by(Result.swap_id.desc()).paginate(
                page_index, self.num_per_page, False).items

            # result
            records = []
            def getMinconf(coin, token):
                if coin == 'ETH' or coin == 'ETHToken':
                    coin = 'ETP'
                elif coin == 'ETP' and token == 'ETH':
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

        @self.app.route('/status/<coin>/<token>/<date>/<int:status>/<int:page_index>')
        @self.app.route('/status/<coin>/<token>/<date>/<int:status>')
        def swap_status(coin, token, date, status=0,page_index=1):
            start_date, end_date = self.parse_date(date)
            if status == 0:
                query = Result.query.filter(and_(
                    Result.date >= start_date, Result.date <= end_date,
                    Result.coin == coin, Result.token == token)).order_by(
                    Result.swap_id.desc())
            elif status == 1:
                query = Result.query.filter(and_(
                    Result.date >= start_date, Result.date <= end_date,
                    Result.coin == coin, Result.token == token,
                    Result.status == int(Status.Swap_Finish))).order_by(
                    Result.swap_id.desc())
            elif status == 2:
                query = Result.query.filter(and_(
                    Result.date >= start_date, Result.date <= end_date,
                    Result.coin == coin, Result.token == token,
                    Result.status != int(Status.Swap_Finish))).order_by(
                    Result.swap_id.desc())
            else:
                return response.make_response(response.ERR_BAD_PARAMETER)

            page_index, results = self.paginate(query, page_index)

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

            return render_template('status.html',
                                   coin=coin, token=token,
                                   date=date, status=status, page_index=page_index,
                                   results=records)

        @self.app.route('/date/<date>/<int:page_index>')
        @self.app.route('/date/<date>')
        def swap_date(date,page_index=1):
            query = Result.query.filter_by(date=date).order_by(
                Result.swap_id.desc())
            page_index, results = self.paginate(query, page_index)
            
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

            return render_template('date.html', date=date, results=records, page_index=page_index)

        @self.app.route('/token/<token>/<int:page_index>')
        @self.app.route('/token/<token>')
        def swap_token(token, page_index=1):
            query = Result.query.filter_by(token=token).order_by(
                    Result.swap_id.desc())
            page_index, results = self.paginate(query, page_index)

            for result in results:
                result.time = self.format_time(result.time)
                result.amount = self.format_amount(result.amount)
                result.fee = self.format_amount(result.from_fee)

            return render_template('token.html', token=token, results=results, page_index=page_index)

        @self.app.route('/report/<date>')
        @self.app.route('/report')
        def report_per_day(date=None):
            if not date:
                date = date_time.get_current_date();

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
                result.rate = self.format_amount(result.rate)
                result.fee = self.format_amount(result.from_fee)
                result.status = constants.StatusStr[result.status]
                return render_template('transaction.html', tx_from=tx_from,  result=result)
            else:
                return response.make_response(response.ERR_INVALID_TRANSACTION)

        @self.app.route('/address/<address>/<int:page_index>')
        @self.app.route('/address/<address>')
        def swap_address(address, page_index=1):
            query = Result.query.filter(or_(
                Result.from_address == address, Result.to_address == address)).order_by(
                    Result.swap_id.desc())
            page_index, results = self.paginate(query, page_index)

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

            return render_template('address.html', address=address, results=records, page_index=page_index, binders=binders)

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

        @self.app.route('/ban/<date>/<int:page_index>')
        @self.app.route('/ban/<date>')
        @self.app.route('/ban')
        def swap_ban(date='all', page_index=1):
            if not date:
                date = 'all'

            # paginate
            if date == 'all':
                total_count = Result.query.filter_by(
                    status=int(Status.Swap_Ban)).count()
            else:
                total_count = Result.query.filter(
                    Result.date == int(date), Result.status == int(Status.Swap_Ban)).count()
            
            page_index = self.calculate_page_index(total_count, page_index)

            return render_template('ban.html',  date=date, page_index=page_index)

        @self.app.route('/getBan/<date>/<int:page_index>')
        def getBan(date='all', page_index=1):
            # paginate
            if not date or date == 'all':
                results = Result.query.filter_by(
                    status=int(Status.Swap_Ban)).order_by(Result.swap_id.desc()).paginate(
                    page_index, self.num_per_page, False).items
            else:
                results = Result.query.filter(
                    Result.date == int(date),
                    Result.status == int(Status.Swap_Ban)).order_by(
                    Result.swap_id.desc()).paginate(
                    page_index, self.num_per_page, False).items

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
                result.date = date_time.get_current_date()
                result.time = date_time.get_current_time()
                result.confirm_status = int(Status.Tx_Unconfirm)
                result.tx_hash = None
                result.tx_height = 0
                result.confirm_height = 0
                db.session.add(result)
                db.session.commit()
                return response.make_response(
                    response.ERR_SUCCESS,
                    "retry success, swap_id: %d, coin: %s , token: %s, from: %s, to: %s, amount: %f" % (
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
        return constants.format_amount(amount)

    def format_rough_amount(self, amount):
        if not amount:
            return '0'

        amount_str = '{:0.4f}'.format(float(amount))
        return constants.format_amount_str(amount_str)

    def format_amount_str(self, amount_str):
        return constants.format_amount_str(amount_str)

    def format_time(self, time):
        return "%02d:%02d:%02d" % (
            time // 10000, time // 100 % 100, time % 100)
