import datetime
import time
import os
import sys
import mfcauto
from distutils.version import StrictVersion
import classes.config
import classes.models
import classes.recording
import classes.postprocessing

if __name__ == '__main__':
    if StrictVersion(mfcauto.__version__) < StrictVersion('0.1.4'):
        print('ERROR: Cannot get tags with mfcauto version below 0.1.4. Update mfcauto!')
        exit()

    config = classes.config.Config(os.path.join(sys.path[0], 'config.conf'))
    #when config is edited at runtime and postprocessing is added, we cannot start it
    if config.settings.post_processing_command:
        classes.postprocessing.init_workers(config.settings.post_processing_thread_count)
    next_run = datetime.datetime.now()
    while True:
        if datetime.datetime.now() < next_run:
            time.sleep(0.1)
            continue
        print("another run {}".format(datetime.datetime.now()))
        next_run += datetime.timedelta(seconds=config.settings.interval)
        config.refresh()
        for uid, model in classes.models.get_online_models().items():
            if not config.does_model_pass_filter(model):
                continue
            classes.recording.start_recording(model.session, config)
            print("recording {}: {} ({} viewers) [{}]".format(model.name, model.session['uid'], model.session['rc'], model.tags))
        print('finished run')
