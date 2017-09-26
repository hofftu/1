import datetime
import time
import os
import sys
import classes.config
import classes.models
import classes.recording

if __name__ == '__main__':
    config = classes.config.Config(os.path.join(sys.path[0], 'config.conf'))
    next_run = datetime.datetime.now()
    while True:
        if datetime.datetime.now() < next_run:
            time.sleep(0.1)
            continue
        next_run += datetime.timedelta(seconds=config.settings.interval)
        config.refresh()
        print("another run {}".format(datetime.datetime.now()))

        #live_models = {model for uid, model in classes.models.get_online_models().items()
        #               if config.does_model_pass_filter(model.session)}
        for uid, model in classes.models.get_online_models().items():
            if not config.does_model_pass_filter(model):
                continue
            classes.recording.start_recording(model.session, config)
            print("recording {}: {} ({} viewers)".format(model.name, model.session['uid'], model.session['rc']))
        print('finished run')
