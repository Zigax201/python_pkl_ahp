from flask import Flask, redirect, url_for, session
from flask_cors import CORS
from flask_restful import Api, Resource, reqparse
from flask_mysqldb import MySQL
from authlib.integrations.flask_client import OAuth
import os
from datetime import timedelta
import yaml
import json

import requests

from auth_decorator import login_required

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
api = Api(app)

cors = CORS(app, resources={r"/*": {"Access-Control-Allow-Origin": "*"}})
# CORS(app)

app.secret_key = os.getenv("APP_SECRET_KEY")

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'
app.config['CORS_HEADERS'] = 'Content-Type'

db = yaml.safe_load(open('db.yaml'))

app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)

data_put_args = reqparse.RequestParser()
data_put_args.add_argument("id", type=int, help="id of the data", required=True)

class tableauData(Resource):
    def get(self, id):
        cur = mysql.connection.cursor()
        cur.callproc('calculateAHP1', (id))
        dataAhp = cur.fetchall()
        data = []
        for f in dataAhp:
            dat = {
                'name' : f[0],
                'jumlahAtt1' : f[1],
                'jumlahAtt2' : f[2],
                'jumlahAtt3' : f[3],
                'rataAtt1' : f[4],
                'rataAtt2' : f[5],
                'rataAtt3' : f[6],
                'matrix1' : f[7],
                'matrix2' : f[8],
                'matrix3' : f[9]
            }
            data.append(dat)
        jsonString = json.loads(json.dumps(data, indent=4, sort_keys=True))
        return jsonString

    # def put(self, id):
    #     args = data_put_args.parse_args()
    #     data[id] = args
    #     return data[id], 201

    # def delete(self, id):
    #     abort_if_data_id_doesnt_exist(id)
    #     del data[id]
    #     return '', 200


api.add_resource(tableauData, "/tableauData/<string:id>")

# Session config
app.secret_key = os.getenv("APP_SECRET_KEY")
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

# oAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    # userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',  # This is only needed if using openId to fetch user info
    client_kwargs={'scope': 'https://www.googleapis.com/auth/drive.file'},
)

@app.route('/')
@login_required
def hello_world():
    email = dict(session)['profile']['email']
    return f'Hello, you are logged in as {email}!'

@app.route('/login', methods=['GET', 'POST'])
def login():    
    r = requests.get("http://localhost:8000/login")
    print(r)
    google = oauth.create_client('google')  # create the google oauth client
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/spreadsheet', methods=['GET', 'POST'])
def spreedsheet():
    if request.method == 'GET':
        return make_response('failure')
    if request.method == 'POST':

        create_row_data = {'message': "Test"}
        
        response = requests.post(
            url, data=json.dumps(create_row_data),
            headers={'Content-Type': 'application/json'}
        )
        return response.content

@app.route('/authorize')
def authorize():
    # idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
    # userid = idinfo['sub']
    google = oauth.create_client('google')  # create the google oauth client
    token = google.authorize_access_token()  # Access token from google (needed to get user info)
    resp = google.get('userinfo')  # userinfo contains stuff u specificed in the scrope
    user_info = resp.json()
    user = oauth.google.userinfo()  # uses openid endpoint to fetch user info
    # Here you use the profile/user data that you got and query your database find/register the user
    # and set ur own data in the session not the profile from google
    session['profile'] = user_info
    session.permanent = True  # make the session permanant so it keeps existing after broweser gets closed
    print()
    return redirect('http://localhost:8000/dashboard')


@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('http://localhost:8000/')



if __name__ == "__main__":
    app.run(debug=True)
