class IBusiness:

    def __init__(self, service, rpc, setting):
        self.service = service
        self.rpc = rpc
        self.setting = setting

    def post(self, f):
        self.service.post(f)

    def start(self):
        pass
        # db.session = self.service.db_session
