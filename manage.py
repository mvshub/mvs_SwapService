from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand
from models.coin import Coin
from models.binder import Binder
from models.result import Result
from models.swap import Swap
from models.swap_ban import Swap_ban
from models.swap_ban import Swap_ban
from models.immature import Immature
from models.scan import Scan

import json
from models import db

setting_filename = 'config/service.json'
settings = json.loads(open(setting_filename).read())

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://%s:%s@%s:%s/%s' % (
    settings['mysql_user'],
    settings['mysql_passwd'],
    settings['mysql_host'],
    settings['mysql_port'],
    settings['mysql_db']
    )

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['extend_existing'] = True


migrate = Migrate(app, db)
manager = Manager(app)


manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()