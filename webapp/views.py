from webapp import app
import flask

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
    return check_login() or flask.render_template('start_page.html')

@app.route('/MFC/wanted')
def wanted():
    return check_login() or flask.render_template('wanted.html', wanted=CONFIG.filter.wanted.dict)

@app.route('/MFC/config', methods=['GET', 'POST'])
def config():
    check = check_login()
    if check is not None:
        return check

    if flask.request.method == 'POST':
        print(flask.request.form)

    return flask.render_template('config.html', config=CONFIG)