import asyncio, requests, pickle, os, sys
from mfcauto import Client, Model, FCTYPE, STATE
if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

result = requests.get('http://www.myfreecams.com/_js/serverconfig.js').json()
servers = result['h5video_servers'].keys()
models = {'online':[]}
def getOnlineModels():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = Client(loop)
    def query():
        try:
            for model in Model.find_models(lambda m: m.bestsession["vs"] == STATE.FreeChat.value and str(m.bestsession['camserv']) in servers):
                models['online'].append(model.bestsession)
        except:client.disconnect()

    def checkTags(p):
        if p.smessage['msg']['arg2'] == 20:
            url = "http://www.myfreecams.com/php/FcwExtResp.php?"
            for name in ["respkey", "type", "opts", "serv"]:
                if name in p.smessage:
                    url += "{}={}&".format(name, p.smessage.setdefault(name, None))
            models['Tags'] = requests.get(url).json()['rdata']

            client.disconnect()

    client.on(FCTYPE.CLIENT_MODELSLOADED, query)
    client.on(FCTYPE.EXTDATA, lambda p: checkTags(p))
    try:
        loop.run_until_complete(client.connect())
        loop.run_forever()
    except:
        pass
    loop.close()
    for model in models['online']:
        try:
            model['tags'] = models['Tags'][str(model['uid'])]
            model['image'] = "https://snap.mfcimg.com/snapimg/{}/400x320/mfc_{}.jpg".format(model['camserv'], model['uid'])
            model['avatar'] = "http://img.mfcimg.com/photos2/{}/{}/avatar.300x300.jpg".format(str(model['uid'])[0:3], model['uid'])
        except:
            model['tags'] = []
    try:
        models.pop('Tags')
    except:
        pass
    with open(os.path.dirname(sys.argv[0]) + '/models.pickle', 'wb') as handle:
        pickle.dump(models, handle, protocol=pickle.HIGHEST_PROTOCOL)

if __name__ == '__main__':
    print("____________________Connection Status____________________")
    getOnlineModels()
