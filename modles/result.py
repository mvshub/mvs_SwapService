from . import db
import time


class Result(db.Model):
    __tablename__ = 'result'

    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    swap_id= db.Column(db.Integer, nullable = False)   
    from_address = db.Column(db.String(128), nullable=False)
    to_address = db.Column(db.String(128), nullable=False)   
    amount = db.Column(db.Numeric(64, 18), nullable=False)

    coin = db.Column(db.String(64), nullable=False)
    token = db.Column(db.String(64), nullable=False)

    tx_hash = db.Column(db.String(256) )  
    is_confirm = db.Column(db.Integer,default = 0)
    status = db.Column(db.Integer,default = 0)
    tx_time = db.Column(db.Numeric(32),default = 0)
    confirm_time = db.Column(db.Numeric(32),default = 0)


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
        dep.is_confirm = dep_.is_confirm
        dep.status = dep_.status
        dep.tx_time = dep_.tx_time
        dep.confirm_time = dep_.confirm_time


        return dep
