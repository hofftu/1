import threading
import requests
import mfcauto

SERVER_CONFIG_URL = 'http://www.myfreecams.com/_js/serverconfig.js'

def get_online_models():
    '''returns a dictionary of all online models in free chat'''
    server_config = requests.get(SERVER_CONFIG_URL).json()
    servers = server_config['h5video_servers'].keys()
    models = {}
    models_lock = threading.Lock()

    def on_tags(_):
        '''function for the TAGS event in mfcclient'''
        nonlocal models

        #locking to prevent from disconnecting too early
        with models_lock:
            #test for data in models. Data in models means that we
            #already had this function running and we can disconnect safely
            if models:
                client.disconnect()
                return

            #merging tags and models (needed due to a possible bug in mfcauto)
            all_results = mfcauto.Model.find_models(lambda m: True)
            print(all_results)
            for element in all_results:
                uid = int(element.uid)
                if uid not in models.keys():
                    models[uid] = Model(element)
                    continue
                model = models[uid]
                models[uid] = model.merge_tags(element)
                #at this point we have a merged object, so we can filter
                if model.session['vs'] != mfcauto.STATE.FreeChat or str(model.session['camserv']) not in servers:
                    models.pop(uid)

    #we dont want to query the models in CLIENT_MODELSLOADED, because we are
    #missing the tags at this point. Rather query everything on TAGS
    client = mfcauto.SimpleClient()
    client.on(mfcauto.FCTYPE.CLIENT_MODELSLOADED, lambda: None)
    client.on(mfcauto.FCTYPE.TAGS, on_tags)
    client.connect()

    return models

class Model():
    '''custom Model class to preserve the session information'''
    def __init__(self, model):
        self.name = model.nm
        self.uid = model.uid
        self.tags = model.tags
        #vs info will be lost
        self.session = model.bestsession

    def __repr__(self):
        return '{{"name": {}, "uid": {}, "tags": {}, "session": {}}}'.format(
            self.name, self.uid, self.tags, self.session)

    def merge_tags(self, model):
        '''merges tags into a model or vice versa and returns new object'''
        base = self if self.tags is None else model
        base.tags = self.tags if self.tags is not None else model.tags
        return base
