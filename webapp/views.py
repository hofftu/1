from webapp import app
import flask
import classes

def init_data(config):
    global CONFIG
    CONFIG = config

def check_login():
    print(flask.session.get('logged_in', None))
    if flask.session.get('logged_in', None) is None:
        return flask.redirect(flask.url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if flask.request.method == 'POST':
        if (flask.request.form['username'] != CONFIG.settings.username
                or flask.request.form['password'] != CONFIG.settings.password):
            error = 'Invalid username/password'
        else:
            flask.session['logged_in'] = True
            flask.flash('Successfully logged in!')
            return flask.redirect(flask.url_for('start_page'))
    return flask.render_template('login.html', error=error)

@app.route('/logout')
def logout():
    flask.session.pop('logged_in', None)
    return flask.redirect(flask.url_for('start_page'))

@app.route('/')
def start_page():
    return check_login() or flask.render_template('start_page.html', recording=classes.recording.RecordingThread.currently_recording_models)

@app.route('/MFC/wanted', methods=['GET', 'POST'])
def wanted():
    check = check_login()
    if check is not None:
        return check

    if flask.request.method == 'POST':
        CONFIG.filter.wanted.set_dict(flask.request.form)

    return flask.render_template('wanted.html', wanted=CONFIG.filter.wanted.dict)

@app.route('/MFC/config', methods=['GET', 'POST'])
def config():
    check = check_login()
    if check is not None:
        return check

    if flask.request.method == 'POST':
        CONFIG.update(flask.request.form)

    return flask.render_template('config.html', config=CONFIG)

@app.route('/MFC/add', methods=['POST'])
def add():
    return check_login() or add_or_remove(_add)

def _add(uid, name):
    result = CONFIG.filter.wanted.add(uid, name)
    if result is None:
        flask.flash('{} with uid {} successfully added'.format(name, uid), 'success')
    else:
        flask.flash('{} with uid {} already in wanted list (named "{}")'.format(name, uid, result['custom_name']), 'info')

@app.route('/MFC/remove', methods=['POST'])
def remove():
    return check_login() or add_or_remove(_remove)

def _remove(uid, name):
    result = CONFIG.filter.wanted.remove(uid)
    if result is not None:
        flask.flash('{} with uid {} (named "{}") successfully removed'.format(name, uid, result['custom_name']), 'success')
    else:
        flask.flash('{} with uid {} not in wanted list'.format(name, uid), 'info')

def add_or_remove(action):
    uid_or_name = classes.helpers.try_eval(flask.request.form['uid_or_name'])
    result = classes.models.get_model(uid_or_name)
    if result is None:
        flask.flash('uid or name "{}" not found'.format(uid_or_name), 'error')
    else:
        action(*result)
    return flask.redirect(flask.url_for('start_page'))
