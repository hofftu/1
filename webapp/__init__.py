from flask import Flask
from flask_scss import Scss

app = Flask(__name__)
scss = Scss(app)
scss.update_scss()

import webapp.views