import asyncio, requests, pickle, sys, os
from mfcauto import Client, Model, FCTYPE, STATE
if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
else:
    import blessings
try:
    term = blessings.Terminal()
except:
    term = False
result = requests.get('http://www.myfreecams.com/_js/serverconfig.js').json()
servers = result['h5video_servers'].keys()
models = {'online':[]}

def getOnlineModels():
    if term:
        term.move(0, 2)
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
        except:
            model['tags'] = []
    try:
        models.pop('Tags')
    except:
        pass
    with open('models.pickle', 'wb') as handle:
        pickle.dump(models, handle, protocol=pickle.HIGHEST_PROTOCOL)

if __name__ == '__main__':
    if term:
        with term.location(0,0):
            sys.stdout.write("\033[K")
            sys.stdout.write("\033[F")
            print("____________________Connection Status____________________")
    else:
        sys.stdout.write("\033[K")
        sys.stdout.write("\033[F")
        print("____________________Connection Status____________________")
    getOnlineModels()
