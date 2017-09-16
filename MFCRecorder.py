import time, datetime, os, threading, sys, configparser, pickle, platform, requests
if os.name == 'nt':
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
from livestreamer import Livestreamer
from queue import Queue
from flask import Flask, render_template, request, redirect, url_for
from subprocess import Popen, PIPE, call
from colorama import Fore

app = Flask(__name__)
mainDir = sys.path[0]
Config = configparser.ConfigParser()

def readConfig():
    global setting
    global filter
    Config.read(mainDir + "/config.conf")
    setting = {
        'save_directory': Config.get('paths', 'save_directory'),
        'wishlist': Config.get('paths', 'wishlist'),
        'blacklist': Config.get('paths', 'blacklist'),
        'interval': int(Config.get('settings', 'checkInterval')),
        'directory_structure': Config.get('paths', 'directory_structure').lower(),
        'postProcessingCommand': Config.get('settings', 'postProcessingCommand'),
        'port': int(Config.get('web', 'port')),
        'minSpace': int(Config.get('settings', 'minSpace')),
        }
    if not setting['minSpace']:setting['minSpace'] = 0
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
        setting['postProcessingThreads'] = int(Config.get('settings', 'postProcessingThreads'))
    except ValueError:
        if setting['postProcessingCommand'] and not setting['postProcessingThreads']:
            setting['postProcessingThreads'] = 1
    setting['completed_directory'] = Config.get('paths', 'completed_directory').lower()
    if not os.path.exists("{path}".format(path=setting['save_directory'])):
        os.makedirs("{path}".format(path=setting['save_directory']))
setting = {}
filter = {}
recording = {}
modelDict = {}
uptime = {}
models={}
startTime = int(time.time())
totalData = 0
fileCount = 0


def getUptime():
    uptime['days'], rem = divmod(int(time.time()) - startTime, 86400)
    uptime['hours'], rem = divmod(rem, 3600)
    uptime['minutes'], uptime['seconds'] = divmod(rem, 60)
    for unit in ['hours', 'minutes', 'seconds']:
        uptime[unit] = str('{:02}'.format(uptime[unit]))
    return uptime

def get_free_space():
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(setting['save_directory']), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value / 1024 / 1024
    else:
        st = os.statvfs(setting['save_directory'])
        return st.f_bavail * st.f_frsize / 1024 / 1024 / 1024

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
        # myfreecams blocks requests for the avatar image if they are referred from a site other than myfreecams.com so were going to download images to static folder
        if not os.path.exists(mainDir + "/static/avatars/{}.jpg".format(model['uid'])):
            try:
                response = requests.get(model['avatar'])
                if response.status_code == 200:
                    with open(mainDir + "/static/avatars/{}.jpg".format(model['uid']), 'wb') as f:
                        f.write(response.content)
                        f.close()
            except (requests.exceptions.ConnectionError, requests.exceptions.MissingSchema):pass
        thread = threading.Thread(target=startRecording, args=(session,))
        thread.start()
        print(Fore.GREEN + 'starting capture of model: {}  condition: {}'.format(model['nm'], session['condition']) + Fore.RESET) if model['condition']\
            else print(Fore.GREEN +'starting capture of model: {}  condition: wanted'.format(model['nm']) + Fore.RESET)
        return True

def getOnlineModels():
    global models
    filter['wanted'] = []
    with open(setting['wishlist']) as f:
        models = list(set(f.readlines()))
        for theModel in models:
            filter['wanted'].append(int(theModel))
        f.close()
    filter['blacklisted'] = []
    if setting['blacklist']:
        with open(setting['blacklist'], 'r') as f:
            models = list(set(f.readlines()))
            for theModel in models:
                filter['blacklisted'].append(int(theModel))
        f.close()
    Config.read(mainDir + "/config.conf")
    filter['minTags'] = int(Config.get('AutoRecording', 'minTags'))
    filter['wantedTags'] = [x.strip().lower() for x in Config.get('AutoRecording', 'tags').split(',')]
    while True:
        timeout = 20
        p = Popen([sys.executable, mainDir + "/getModels.py"])
        t = 0
        while t < timeout and p.poll() is None:
            time.sleep(1)
            t += 1
        if p.poll() is None:
            p.terminate()
            print('connection failed')
        else:
            with open(mainDir + '/models.pickle', 'rb') as handle:
                models = pickle.load(handle)
                handle.close()
            now = int(time.time())
            for model in models['online']:
                modelDict[model['uid']] = model
                if model['uid'] not in recording.keys():
                    recordModel(model, now)
                else:
                    recording[model['uid']]['rc'] = model['rc']
            break

def startRecording(model):
    global totalData
    global fileCount
    fileSize = 0
    try:
        recording[model['uid']] = model
        session = Livestreamer()
        streams = session.streams("hlsvariant://http://video{srv}.myfreecams.com:1935/NxServer/ngrp:mfc_{id}.f4v_mobile/playlist.m3u8"
          .format(id=(int(model['uid']) + 100000000),
            srv=(int(model['camserv']) - 500)))
        if 'best' in streams.keys():
            stream = streams["best"]
            with stream.open() as fd:
                now = datetime.datetime.now()
                filePath = setting['directory_structure'].format(path=setting['save_directory'], model=model['nm'], uid=model['uid'],
                                                      seconds=now.strftime("%S"), day=now.strftime("%d"),
                                                      minutes=now.strftime("%M"), hour=now.strftime("%H"),
                                                      month=now.strftime("%m"), year=now.strftime("%Y"), auto=model['condition'])
                directory = filePath.rsplit('/', 1)[0]+'/'
                if not os.path.exists(directory):
                    os.makedirs(directory)
                fileCount += 1
                with open(filePath, 'wb') as f:
                    minViewers = filter['autoStopViewers'] if model['condition'] == 'VIEWERS_' else filter['stopViewers']
                    while modelDict[model['uid']]['rc'] >= minViewers and availableSpace > setting['minSpace']\
                            and model['uid'] not in filter['blacklisted']:
                        try:
                            data = fd.read(1024)
                            f.write(data)
                            totalData += 1024
                            fileSize += 1024
                        except:
                            break
                    f.close()
                    if fileSize == 0:
                        fileCount -= 1
                        os.remove(filePath)
                    else:
                        if setting['postProcessingCommand']:
                            processingQueue.put({'model':model['nm'], 'path': filePath, 'uid':model['uid']})
                        elif setting['completed_directory']:
                            finishedDir = setting['completed_directory'].format(path=setting['save_directory'], model=model, uid=model['uid'],
                                                                     seconds=now.strftime("%S"), minutes=now.strftime("%M"),
                                                                     hour=now.strftime("%H"), day=now.strftime("%d"),
                                                                     month=now.strftime("%m"), year=now.strftime("%Y"), auto=model['condition'])
                            if not os.path.exists(finishedDir):
                                os.makedirs(setting['finishedDir'])
                            os.rename(filePath, setting['finishedDir']+'/'+filePath.rsplit('/', 1)[1])
    finally:
        recording.pop(model['uid'], None)
        print(Fore.RED + "{}'s session has ended".format(model['nm']) + Fore.RESET)

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
        call(setting['postProcessingCommand'].split() + [path, filename, directory, model, uid])

@app.route('/', methods=['GET'])
@app.route('/mfc', methods=['GET'])
def root():
    return redirect(url_for('home'), code=302)

def getSettings():
    f = open(sys.path[0] + "/config.conf")
    settings = {}
    lines = (f.readlines())
    for line in lines:
        try:
            if line.split()[1] == "=":
                settings[line.split(' = ')[0]] = line.split(' = ')[1].strip('\n')
        except IndexError:
            settings[line.split(' = ')[0].strip('\n')] = ""
    return settings

@app.route('/MFC')
def home():
    addUID = request.args.get('addUID')
    blockUID = request.args.get('blockUID')
    removeUID = request.args.get('removeUID')
    sortValue = request.args.get('sort')
    if addUID:
        f = open(setting['wishlist'], 'a')
        f.write(str(addUID) + '\n')
        print("model with UID {} has been added to the wishlist".format(addUID))
        f.close()
        if int(addUID) in recording.keys():
            recording[int(addUID)]['condition'] = ""
            return redirect(url_for('home'), code=302) if not sortValue else redirect(url_for('home')+'?sort='+sortValue, code=302)
    if blockUID:
        f= open(setting['blacklist'], 'a')
        f.write(str(blockUID) + '\n')
        print("model with UID {} has been added to the blacklist".format(blockUID))
        f.close()
        filter['blacklisted'].append(blockUID)
        return redirect(url_for('home'), code=302) if not sortValue else redirect(url_for('home') + '?sort=' + sortValue, code=302)
    if removeUID:
        with open(setting['wishlist']) as f:
            lines = list(set(f.readlines()))
            f.close()
        f = open(setting['wishlist'], 'w')
        for line in lines:
            if line != removeUID+'\n':
                f.write(line)
        f.close()
        if int(removeUID) in recording.keys():
            recording[int(removeUID)]['condition'] = "Removed"
        return redirect(url_for('home'), code=302) if not sortValue else  redirect(url_for('home') + '?sort=' + sortValue, code=302)
    sortValue = request.args.get('sort')
    if sortValue is None:
        sortValue = 'rc'
    order = sorted(recording.values(), key=lambda k: int(k[sortValue]), reverse=True) if sortValue != 'nm' else sorted(recording.values(), key=lambda k: k[sortValue].lower())
    return render_template('MFC.html', count=len(recording), models=order, uptime=getUptime(), sortValue=sortValue,
                           freeSpace=round(get_free_space(),2), totalData=round(totalData / 1024 / 1024 / 1024, 2), fileCount=fileCount)

@app.route('/MFC/config')
def config():
    return render_template('config.html', settings=getSettings())

@app.route('/', methods=['POST'])
def parse_data():
    data = dict(request.form)
    print(data)
    if "power" in data.keys():
        print('power')
        if data['power'][0] == 'restart':
            os.execl(sys.executable, sys.executable, *sys.argv)
            return "Restarting"
    if 'text' in data.keys():
        p = Popen([sys.executable, mainDir + "/add.py", data], stdout=PIPE)
        out = p.communicate()
        if 'has been added to the list' in str(out):
            return str('{} has been added to the wanted list'.format(data))
        elif 'is already in the wanted list' in str(out):
            return str('{} is already in the wanted list'.format(data))
        else:
            return 'something went wrong adding the model'
    else:
        if 'wishlist' in request.form.keys():
            f = open(sys.path[0] + "/config.conf")

            lines = (f.readlines())
            f = open(sys.path[0] + "/config.conf", 'w')
            for line in lines:
                try:
                    if line.split()[1] == "=":
                        var = line.split()[0]
                        value = line.split()[2]
                        if data[var][0]:
                            print(var, data[var])
                            f.write("{} = {}\n".format(var, data[var][0]))
                        else:
                            f.write(line)
                    else:
                        f.write(line)

                except:
                    f.write(line)
            f.close()
            readConfig()
            return redirect(url_for('home'), code=302)
    return "Hello world"

def block():
    #TODO add block button to web ui
    pass

#TODO create *monkey scripts to add/block users
#TODO impliment SQL DB for better tracking of data over time

if __name__ == '__main__':
    readConfig()
    t = threading.Thread(target=app.run, kwargs={'host':'0.0.0.0', 'port': setting['port'], 'threaded':'True'})
    t.start()
    if setting['postProcessingCommand']:
        processingQueue = Queue()
        postprocessingWorkers = []
        for i in range(0, setting['postProcessingThreads']):
            t = threading.Thread(target=postProcess)
            postprocessingWorkers.append(t)
            t.start()
    while True:
        availableSpace = get_free_space()
        if availableSpace < setting['minSpace']:
            print(Fore.RED + "available disk space is less than minimum space setting. recordings are stopped until more space is available\n"
                             "{} GB available".format(round(availableSpace, 2)) + Fore.RESET)
        else:
            while get_free_space() < setting['minSpace']:
                time.sleep(1)
        getOnlineModels()
        print("Disconnected: Found " + Fore.BLUE + str(len(models['online'])) + Fore.RESET + " models in public chat")
        print("____________________Recording Status_____________________")
        print("{} model(s) are being recorded. Next check in {} seconds".format(len(recording), setting['interval']))
        print("the following models are being recorded: {}".format([recording[x]['nm'] for x in recording.keys()]))
        time.sleep(setting['interval'])
