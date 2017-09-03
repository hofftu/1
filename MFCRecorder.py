import time, datetime, os, threading, sys, configparser, subprocess, pickle
if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
else:
    import blessings
from livestreamer import Livestreamer
from queue import Queue

try:
    term = blessings.Terminal()
except:
    term = False
term = False
Config = configparser.ConfigParser()
Config.read(sys.path[0] + "/config.conf")
save_directory = Config.get('paths', 'save_directory')
wishlist = Config.get('paths', 'wishlist')
blacklist = Config.get('paths', 'blacklist')
interval = int(Config.get('settings', 'checkInterval'))
directory_structure = Config.get('paths', 'directory_structure').lower()
postProcessingCommand = Config.get('settings', 'postProcessingCommand')
filter = {
    'minViewers': int(Config.get('settings', 'minViewers')),
    'viewers': int(Config.get('AutoRecording', 'viewers')),
    'newerThanHours': int(Config.get('AutoRecording', 'newerThanHours')),
    'score': int(Config.get('AutoRecording', 'score')),
    'autoStopViewers': int(Config.get('AutoRecording', 'autoStopViewers')),
    'stopViewers': int(Config.get('settings', 'StopViewers')),
    'blacklisted': [],
    'wanted': []}

if filter['stopViewers'] > filter['minViewers']:filter['minViewers'] = filter['stopViewers']
if filter['viewers'] < filter['autoStopViewers']:filter['viewers'] = filter['autoStopViewers']

try:
    postProcessingThreads = int(Config.get('settings', 'postProcessingThreads'))
except ValueError:
    pass
completed_directory = Config.get('paths', 'completed_directory').lower()


if not os.path.exists("{path}".format(path=save_directory)):
    os.makedirs("{path}".format(path=save_directory))

recording = {}
modelDict = {}

def recordModel(model, now):
    session = model

    def check():
        if session['uid'] in filter['wanted']:
            if filter['minViewers'] and session['rc'] < filter['minViewers']:
                return False
            else:
                session['condition'] = ''
                return True
        if session['uid'] in filter['blacklisted']:
            return False
        if filter['newerThanHours'] and session['creation'] > now - filter['newerThanHours'] * 60 * 60:
            session['condition'] = 'NEW_'
            return True
        if filter['viewers'] and session['rc'] > filter['viewers']:
            session['condition'] = 'VIEWERS_'
            return True
        if filter['score'] and session['camscore'] > filter['score']:
            session['condition'] = 'SCORE_'
            return True
        if filter['wantedTags'] and filter['minTags']:
            session['tags'] = [x.strip().lower() for x in session['tags']]
            if len([element for element in filter['wantedTags'] if element in session['tags']]) >= filter['minTags']:
                session['condition'] = 'TAGS_'
                return True
        return False
    if check():
        thread = threading.Thread(target=startRecording, args=(session,))
        thread.start()
        return True

def getOnlineModels():
    global models
    filter['wanted'] = []
    with open(wishlist) as f:
        models = list(set(f.readlines()))
        for theModel in models:
            filter['wanted'].append(int(theModel))
    f.close()
    filter['blacklisted'] = []
    if blacklist:
        with open(blacklist) as f:
            models = list(set(f.readlines()))
            for theModel in models:
                filter['blacklisted'].append(int(theModel))
        f.close()
    Config.read(sys.path[0] + "/config.conf")
    filter['minTags'] = int(Config.get('AutoRecording', 'minTags'))
    filter['wantedTags'] = [x.strip().lower() for x in Config.get('AutoRecording', 'tags').split(',')]
    timeout = 5
    p = subprocess.Popen([sys.executable, sys.path[0] + "/getModels.py"])
    t = 0
    while t < timeout and p.poll() is None:
        time.sleep(1)
        t += 1
    if p.poll() is None:
        p.terminate()
        print('connection failed')
    else:
        with open('models.pickle', 'rb') as handle:
            models = pickle.load(handle)
        now = int(time.time())
        for model in models['online']:
            modelDict[model['uid']] = model
            if model['uid'] not in recording.keys() and model['nm'] not in recording.values():
                recordModel(model, now)




def startRecording(model):
    try:
        recording[model['uid']] = model['nm']
        session = Livestreamer()
        streams = session.streams("hlsvariant://http://video{srv}.myfreecams.com:1935/NxServer/ngrp:mfc_{id}.f4v_mobile/playlist.m3u8"
          .format(id=(int(model['uid']) + 100000000),
            srv=(int(model['camserv']) - 500)))
        stream = streams["best"]
        fd = stream.open()
        now = datetime.datetime.now()
        filePath = directory_structure.format(path=save_directory, model=model['nm'], uid=model['uid'],
                                              seconds=now.strftime("%S"), day=now.strftime("%d"),
                                              minutes=now.strftime("%M"), hour=now.strftime("%H"),
                                              month=now.strftime("%m"), year=now.strftime("%Y"), auto=model['condition'])
        directory = filePath.rsplit('/', 1)[0]+'/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(filePath, 'wb') as f:
            minViewers = filter['autoStopViewers'] if model['condition'] == 'viewers' else filter['stopViewers']
            attempt = 1
            while modelDict[model['uid']]['rc'] >= minViewers and attempt <= 5:
                try:
                    data = fd.read(1024)
                    f.write(data)
                    attempt = 1
                except:
                    attempt += 1
            f.close()

            if postProcessingCommand:
                processingQueue.put({'model':model['nm'], 'path': filePath, 'uid':model['uid']})
            elif completed_directory:
                finishedDir = completed_directory.format(path=save_directory, model=model, uid=model['uid'],
                                                         seconds=now.strftime("%S"), minutes=now.strftime("%M"),
                                                         hour=now.strftime("%H"), day=now.strftime("%d"),
                                                         month=now.strftime("%m"), year=now.strftime("%Y"), auto=model['condition'])
                if not os.path.exists(finishedDir):
                    os.makedirs(finishedDir)
                os.rename(filePath, finishedDir+'/'+filePath.rsplit('/', 1)[1])

    finally:
        recording.pop(model['uid'], None)


def postProcess():
    while True:
        while processingQueue.empty():
            time.sleep(1)
        parameters = processingQueue.get()
        model = parameters['model']
        path = parameters['path']
        filename = path.rsplit('/', 1)[1]
        uid = str(parameters['uid'])
        directory = path.rsplit('/', 1)[0]+'/'
        subprocess.call(postProcessingCommand.split() + [path, filename, directory, model, uid])


if __name__ == '__main__':
    if term:
        for line in range(term.height):
            with term.location(0, line):
                sys.stdout.write("\033[K")
    if postProcessingCommand:
        processingQueue = Queue()
        postprocessingWorkers = []
        for i in range(0, postProcessingThreads):
            t = threading.Thread(target=postProcess)
            postprocessingWorkers.append(t)
            t.start()
    while True:
        if term:
            term.move(0,0)
        getOnlineModels()
        if term:
            with term.location(0,1):
                sys.stdout.write("\033[K")
                print("Disconnected:")
                sys.stdout.write("\033[K")
                print("Waiting for next check")
            with term.location(0,3):
                print("____________________Recording Status_____________________")
            for i in range(interval, 0, -1):
                with term.location(0,4):
                    sys.stdout.write("\033[K")
                    print("{} model(s) are being recorded. Next check in {} seconds".format(len(recording), i))
                    sys.stdout.write("\033[K")
                    print("the following models are being recorded: {}".format(list(recording.values())), end="\r")
                    term.clear_eos()
                    time.sleep(1)
        else:
            sys.stdout.write("\033[K")
            print("Disconnected:")
            sys.stdout.write("\033[K")
            print("Waiting for next check")
            print("____________________Recording Status_____________________")
        for i in range(interval, 0, -1):
            sys.stdout.write("\033[K")
            print("{} model(s) are being recorded. Next check in {} seconds".format(len(recording), i))
            sys.stdout.write("\033[K")
            print("the following models are being recorded: {}".format(list(recording.values())), end="\r")
            time.sleep(1)
