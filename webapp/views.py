from webapp import app
import flask

def init_data(config):
    global CONFIG
    CONFIG = config

@app.route('/MFC/wanted')
def wanted():
    return flask.render_template('wanted.html', wanted=CONFIG.filter.wanted.dict)