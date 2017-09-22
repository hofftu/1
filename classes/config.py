import configparser
import time

class Config:
    class Container:
        #empty class to hold some data
        #alternatively we could model the setting and filter classes...
        pass

    def __init__(self, config_file_path):
        self._config_file_path = config_file_path
        self._parser = configparser.ConfigParser()

    @property
    def settings(self):
        self._parse()
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

        return s

    @property
    def filter(self):
        self._parse()
        f = Config.Container()
        f.min_viewers = int(self._parser.get('settings', 'minViewers'))
        f.viewers = int(self._parser.get('AutoRecording', 'viewers'))
        f.newer_than_hours = int(self._parser.get('AutoRecording', 'newerThanHours'))
        f.score = int(self._parser.get('AutoRecording', 'score'))
        f.auto_stop_viewers = int(self._parser.get('AutoRecording', 'autoStopViewers'))
        f.stop_viewers = int(self._parser.get('settings', 'StopViewers'))
        f.min_tags = int(self._parser.get('AutoRecording', 'minTags'))
        f.wanted_tags = {s.strip().lower() for s in self._parser.get('AutoRecording', 'tags').split(',')}

        settings = self.settings

        f.blacklisted = self._read_uid_list(settings.blacklist_path)
        f.wanted = self._read_uid_list(settings.wishlist_path)

        return f

    def _parse(self):
        self._parser.read(self._config_file_path)

    def _read_uid_list(self, path):
        if not path:
            return set()
        with open(path, 'r') as file:
            return {int(line) for line in file.readlines()} #creates a set

    #maybe belongs more into a filter class, but then we would have to create one
    def does_model_pass_filter(self, session):
        f = self.filter
        if session['uid'] in f.wanted:
            if f.min_viewers and session['rc'] < f.min_viewers:
                return False
            else:
                session['condition'] = ''
                return True
        if session['uid'] in f.blacklisted:
            return False
        if f.newer_than_hours and session['creation'] > int(time.time()) - f.newer_than_hours * 60 * 60:
            session['condition'] = 'NEW_'
            return True
        if f.viewers and session['rc'] > f.viewers:
            session['condition'] = 'VIEWERS_'
            return True
        if f.score and session['camscore'] > f.score:
            session['condition'] = 'SCORE_'
            return True
        if f.wanted_tags and f.min_tags:
            if len(f.wanted_tags.union([s.strip().lower() for s in session['tags']])) >= f.min_tags:
                session['condition'] = 'TAGS_'
                return True
        return False
