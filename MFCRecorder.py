import time, datetime, os, threading, sys, asyncio, configparser
from livestreamer import Livestreamer
from mfcauto import Client, Model, FCTYPE, STATE


Config = configparser.ConfigParser()
Config.read(sys.path[0] + "/config.conf")
save_directory = Config.get('paths', 'save_directory')
wishlist = Config.get('paths', 'wishlist')
interval = int(Config.get('settings', 'checkInterval'))
online = []
if not os.path.exists("{path}".format(path=save_directory)):
    os.makedirs("{path}".format(path=save_directory))

recording = []
recordingNames = []

def getOnlineModels():
    wanted = []
    with open(wishlist) as f:
        for model in f:
            models = model.split()
            for theModel in models:
                wanted.append(int(theModel))
    f.close()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = Client(loop)

    def query():
        try:
            MFConline = Model.find_models(lambda m: m.bestsession["vs"] == STATE.FreeChat.value)
            for model in MFConline:
                if model.bestsession['uid'] in wanted and model.bestsession['uid'] not in recording:
                    thread = threading.Thread(target=startRecording, args=(model.bestsession,))
                    thread.start()
            client.disconnect()
        except:
            client.disconnect()
            pass

            # loop.call_later(20, query)

    client.on(FCTYPE.CLIENT_MODELSLOADED, query)
    try:
        loop.run_until_complete(client.connect())
        loop.run_forever()
    except:
        pass
    loop.close()

def startRecording(model):
    try:
        session = Livestreamer()
        streams = session.streams("hlsvariant://http://video{srv}.myfreecams.com:1935/NxServer/ngrp:mfc_{id}.f4v_mobile/playlist.m3u8"
          .format(id=(int(model['uid']) + 100000000),
            srv=(int(model['camserv']) - 500)))
        stream = streams["best"]
        fd = stream.open()
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime("%Y.%m.%d_%H.%M.%S")
        if not os.path.exists("{path}/{model}".format(path=save_directory, model=model['uid'])):
            os.makedirs("{path}/{model}".format(path=save_directory, model=model['uid']))
        with open("{path}/{uid}/{st}_{model}.mp4".format(path=save_directory, uid=model['uid'], model=model['nm'],
                                                           st=st), 'wb') as f:
            recording.append(model['uid'])
            recordingNames.append(model['nm'])
            while True:
                try:
                    data = fd.read(1024)
                    f.write(data)
                except:
                    f.close()
                    recording.remove(model['uid'])
                    recordingNames.remove(model['nm'])
                    return

        if model in recording:
            recording.remove(model['uid'])
            recordingNames.remove(model['nm'])
    except:
        if model in recording:
            recording.remove(model['uid'])
            recordingNames.remove(model['nm'])


if __name__ == '__main__':
    print("____________________Connection Status____________________")
    while True:
        getOnlineModels()
        sys.stdout.write("\033[F")
        sys.stdout.write("\033[K")
        sys.stdout.write("\033[F")
        sys.stdout.write("\033[K")
        sys.stdout.write("\033[F")
        sys.stdout.write("\033[F")
        print()
        print()
        print("Disconnected:")
        print("Waiting for next check")
        print("____________________Recording Status_____________________")
        for i in range(20, 0, -1):
            sys.stdout.write("\033[K")
            print("{} model(s) are being recorded. Next check in {} seconds".format(len(recording), i))
            sys.stdout.write("\033[K")
            print("the following models are being recorded: {}".format(recordingNames), end="\r")
            time.sleep(1)
            sys.stdout.write("\033[F")
        sys.stdout.write("\033[F")
        sys.stdout.write("\033[F")
        sys.stdout.write("\033[F")
