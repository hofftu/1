import configparser
import time
import os
import platform
import ctypes

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

    def _read_settings(self):
        s = Config.Container()
        s.save_directory = self._parser.get('paths', 'save_directory')
        s.wishlist_path = self._parser.get('paths', 'wishlist')
        s.blacklist_path = self._parser.get('paths', 'blacklist')
        s.interval = int(self._parser.get('settings', 'checkInterval'))
        s.directory_structure = self._parser.get('paths', 'directory_structure').lower()
        s.post_processing_command = self._parser.get('settings', 'postProcessingCommand')
        s.port = int(self._parser.get('web', 'port'))
        s.min_space = int(self._parser.get('settings', 'minSpace'))
        s.completed_directory = self._parser.get('paths', 'completed_directory').lower()

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

        f.blacklisted = self._read_uid_list(self.settings.blacklist_path)
        f.wanted = self._read_uid_list(self.settings.wishlist_path)

        self._filter = f

    def refresh(self):
        '''load config again to get fresh values'''
        self._parse()
        self._read_settings()
        self._read_filter()
        self._available_space = self._get_free_diskspace()

    def _parse(self):
        self._parser.read(self._config_file_path)

    def _read_uid_list(self, path):
        if not path:
            return set()
        with open(path, 'r') as file:
            return {int(line) for line in file.readlines()} #creates a set

    #maybe belongs more into a filter class, but then we would have to create one
    def does_model_pass_filter(self, model):
        '''determines whether a recording should start'''
        f = self.filter
        if model.uid in f.wanted:
            if f.min_viewers and model.session['rc'] < f.min_viewers:
                return False
            else:
                model.session['condition'] = ''
                return True
        if model.uid in f.blacklisted:
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
        if (f.wanted_tags and
                len(f.wanted_tags.intersection(model.tags if model.tags is not None else [])) >= f.min_tags):
            model.session['condition'] = 'TAGS_'
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
        min_viewers = self.filter.auto_stop_viewers if session['condition'] == 'VIEWERS_' else self.filter.stop_viewers
        return (session['rc'] >= min_viewers
                and self._available_space > self.settings.min_space
                and session['uid'] not in self.filter.blacklisted)
    
