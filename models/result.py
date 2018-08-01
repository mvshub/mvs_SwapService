from . import db
import time


class Result(db.Model):
    __tablename__ = 'result'

    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    swap_id = db.Column(db.Integer, nullable=False)
    from_address = db.Column(db.String(128))
    to_address = db.Column(db.String(128))
    amount = db.Column(db.Numeric(64, 18), nullable=False)

    coin = db.Column(db.String(64), nullable=False)
    token = db.Column(db.String(64), nullable=False)

    tx_raw = db.Column(db.String(256))
    tx_hash = db.Column(db.String(256))
    tx_height = db.Column(db.Integer)
    confirm_height = db.Column(db.Integer)
    confirm_status = db.Column(db.Integer, default=0)
    status = db.Column(db.Integer, default=0)
    confirm_date = db.Column(db.Numeric(16), default=0)
    confirm_time = db.Column(db.Numeric(16), default=0)
    message = db.Column(db.Text)

    @classmethod
    def copy(cls, dep_):
        dep = Result()
        dep.iden = dep_.iden
        dep.swap_id = dep_.swap_id
        dep.from_address = dep_.from_address
        dep.to_address = dep_.to_address
        dep.amount = dep_.amount
        dep.token = dep_.token
        dep.coin = dep_.coin
        dep.tx_hash = dep_.tx_hash
        dep.tx_raw = dep_.tx_raw
        dep.confirm_status = dep_.confirm_status
        dep.status = dep_.status
        dep.confirm_date = dep_.confirm_date
        dep.confirm_time = dep_.confirm_time
        dep.message = dep_.message

        return dep

    @classmethod
    def to_json(cls, obj):
        #import pdb; pdb.set_trace()
        return {
            'swap_id' : obj.swap_id,
            'from_address' : obj.from_address,
            'to_address' : obj.to_address,
            'amount' : str(obj.amount),
            'token' : obj.token,
            'coin' : obj.coin,
            'tx_hash' : obj.tx_hash,
            'tx_raw' : obj.tx_raw,
            'confirm_status' : obj.confirm_status,
            'status' : obj.status,
            'confirm_date' : str(obj.confirm_date),
            'confirm_time' : str(obj.confirm_time),
            'message' : obj.message
        }