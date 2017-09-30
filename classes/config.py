import configparser
import time
import os
import platform
import ctypes
import json
import threading

LIST_MODE_WANTED = 0
LIST_MODE_BLACKLISTED = 1

class Config:
    class Container:
        '''empty class to hold some data'''
        #alternatively we could model the setting and filter classes...
        pass

    def __init__(self, config_file_path):
        self._config_file_path = config_file_path
        self._parser = configparser.ConfigParser()
        self.refresh()

    @property
    def settings(self):
        return self._settings

    @property
    def filter(self):
        return self._filter

    def _make_absolute(self, path):
        if not path or os.path.isabs(path):
            return path
        return os.path.join(os.path.dirname(self._config_file_path), path)

    def _read_settings(self):
        s = Config.Container()
        s.save_directory = self._make_absolute(self._parser.get('paths', 'save_directory'))
        s.wishlist_path = self._make_absolute(self._parser.get('paths', 'wishlist'))
        s.interval = int(self._parser.get('settings', 'checkInterval'))
        s.directory_structure = self._parser.get('paths', 'directory_structure').lower()
        s.post_processing_command = self._parser.get('settings', 'postProcessingCommand')
        s.port = int(self._parser.get('web', 'port'))
        s.min_space = int(self._parser.get('settings', 'minSpace'))
        s.completed_directory = self._make_absolute(self._parser.get('paths', 'completed_directory').lower())

        #why do we need exception handling here?
        try:
            s.post_processing_thread_count = int(self._parser.get('settings', 'postProcessingThreads'))
        except ValueError:
            if s.post_processing_command and not s.post_processing_thread_count:
                s.post_processing_thread_count = 1

        #why do we need this check?
        if not s.min_space: s.min_space = 0

        self._settings = s

    def _read_filter(self):
        f = Config.Container()
        f.newer_than_hours = int(self._parser.get('AutoRecording', 'newerThanHours'))
        f.score = int(self._parser.get('AutoRecording', 'score'))
        f.auto_stop_viewers = int(self._parser.get('AutoRecording', 'autoStopViewers'))
        f.stop_viewers = int(self._parser.get('settings', 'StopViewers'))
        f.min_tags = max(1, int(self._parser.get('AutoRecording', 'minTags')))
        f.wanted_tags = {s.strip().lower() for s in self._parser.get('AutoRecording', 'tags').split(',')}
        #account for when stop is greater than min
        f.min_viewers = max(f.stop_viewers, int(self._parser.get('settings', 'minViewers')))
        f.viewers = max(f.auto_stop_viewers, int(self._parser.get('AutoRecording', 'viewers')))

        f.wanted = Wanted(self.settings)

        self._filter = f

    def refresh(self):
        '''load config again to get fresh values'''
        self._parse()
        self._read_settings()
        self._read_filter()
        self._available_space = self._get_free_diskspace()

    def _parse(self):
        self._parser.read(self._config_file_path)

    #maybe belongs more into a filter class, but then we would have to create one
    def does_model_pass_filter(self, model):
        '''determines whether a recording should start'''
        f = self.filter
        if f.wanted.is_wanted(model.uid):
            #TODO: do we want a global min_viewers if model specific is not set??
            if model.session['rc'] < f.wanted.dict[model.uid]['min_viewers']:
                return False
            else:
                model.session['condition'] = ''
                return True
        if f.wanted.is_blacklisted(model.uid):
            return False
        if f.newer_than_hours and model.session['creation'] > int(time.time()) - f.newer_than_hours * 60 * 60:
            model.session['condition'] = 'NEW_'
            return True
        if f.viewers and model.session['rc'] > f.viewers:
            model.session['condition'] = 'VIEWERS_'
            return True
        if f.score and model.session['camscore'] > f.score:
            model.session['condition'] = 'SCORE_'
            return True
        if f.wanted_tags:
            matches = f.wanted_tags.intersection(model.tags if model.tags is not None else [])
            if len(matches) >= f.min_tags:
                model.session['condition'] = '({})_'.format(','.join(matches))
                return True
        return False

    def _get_free_diskspace(self):
        '''https://stackoverflow.com/questions/51658/cross-platform-space-remaining-on-volume-using-python'''
        if platform.system() == 'Windows':
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(self.settings.save_directory), None, None, ctypes.pointer(free_bytes))
            return free_bytes.value / 1024 / 1024
        st = os.fstatvfs(self.settings.save_directory)
        return st.f_bavail * st.f_frsize / 1024 / 1024 / 1024

    def keep_recording(self, session):
        '''determines whether a recording should continue'''
        #would it be possible that no entry is existing if we are already recording?
        #TODO: global stop_viewers if no model specific is set??
        #TODO: stop viewers will also stop recordings based on tags etc.
        min_viewers = self.filter.auto_stop_viewers if session['condition'] == 'VIEWERS_' else self.filter.wanted.dict[session['uid']['stop_viewers']]
        return (session['rc'] >= min_viewers
                and self._available_space > self.settings.min_space
                #TODO: should we really instantaneously stop recording if model was added to blacklist??
                and self.filter.wanted.is_blacklisted(session['uid']))
    
class Wanted():

    def __init__(self, settings):
        self._lock = threading.Lock()
        self._settings = settings
        #create new empty wanted file
        try:
            with open(self._settings.wishlist_path, 'x') as file:
                file.write('{}')
        except FileExistsError:
            pass
        self._load()

    def _load(self):
        with self._lock:
            with open(self._settings.wishlist_path, 'r+') as file:
                self.dict = {int(uid): data for uid, data in json.load(file).items()}

    def set_data(self, uid, enabled=True, list_mode=LIST_MODE_WANTED,
                 custom_name='', comment='', min_viewers=0, stop_viewers=0):
        data = {
            'enabled': enabled,
            'list_mode': list_mode,
            'custom_name': custom_name,
            'comment': comment,
            'min_viewers': min_viewers,
            'stop_viewers': stop_viewers,
        }
        self.set_data_dict(uid, data)

    def set_data_dict(self, uid, data):
        '''set data dictionary for model uid, existing or not'''
        with self._lock:
            self.dict[uid] = data
            with open(self._settings.wishlist_path, 'w') as file:
                json.dump(self.dict, file, indent=4)

    def is_wanted(self, uid):
        '''determines if model is enabled and wanted'''
        return self._is_list_mode_value(uid, LIST_MODE_WANTED)

    def is_blacklisted(self, uid):
        '''determines if model is enabled and blacklisted'''
        return self._is_list_mode_value(uid, LIST_MODE_BLACKLISTED)

    def _is_list_mode_value(self, uid, value):
        '''determines if list_mode equals the specified one, but only if the item is enabled'''
        entry = self.dict.get(uid)
        if not (entry and entry['enabled']):
            return False
        return entry['list_mode'] == value
