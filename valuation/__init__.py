from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
#old sqlite db
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///valuation.db'

#new mysql db
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Password627@localhost/fpldb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from valuation import routes 