# ++++++++++++++++ API ++++++++++++++++
from flask import Flask, jsonify, request, redirect, Response, make_response, url_for, send_from_directory
import flask.ext.restless
import datetime 
import requests
import ast
from json import dumps
from sortedcontainers import SortedList,SortedSet
# +++++++++++++++++ SQLALCHEMY +++++++++
from flask.ext.sqlalchemy import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy import or_
# +++++++++++++++++ File Management ++++
import os
import sys
from werkzeug import secure_filename
from flask.ext.autodoc import Autodoc
from paramiko import SSHClient
from scp import SCPClient
import paramiko





# ++++ Where files are stored +++++

UPLOAD_FOLDER = "C:/Users/sony-vaio/Desktop/demo/uploads"

# ++++ API ++++++++++++++++++++++++

app = Flask(__name__)
auto= Autodoc(app)

#++++ Connection to Database ++++


app.config.from_pyfile('config.py')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)  



def add_visit(file):
    vis = visits()
    vis.name = file
    db.session.add(vis)
    db.session.commit()


# +++++ Predictor +++++++++++++++++++++++++++     


def WEMA(file):

    alpha = 0.8
    filename = file[0]
    current_time = datetime.datetime.utcnow()
    five_minutes_ago = current_time - datetime.timedelta(minutes=5)
    req_last_five_min = db.session.query(visits).filter((visits.date > five_minutes_ago),(visits.name == filename)).count()
    a = req_last_five_min
    b = Content.query.filter_by(name=filename).one()
    y = alpha*a + (1-alpha)*float(b.prediction)
    return y

# +++++ Module that increments number of Hits of a file ++++

def Increment_Hits(file):
    user = Content.query.filter_by(name=file).all()
    user[0].Hits += 1
    db.session.commit()

# ++++++ Database Models +++++++++++++++++++++++ 

class Router(db.Model):

  __tablename__ = 'Router'
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(20))
  type = db.Column(db.String(20))
  ports = db.relationship('ports', backref ='Belong to', lazy='dynamic')

class ports(db.Model):

  __tablename__ = 'ports'
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(20))
  type = db.Column(db.String(20))
  status = db.Column(db.String(20))
  Router_id = db.Column(db.Integer, db.ForeignKey('Router.id'))
  flux = db.relationship('flux' ,backref='Sent from ', lazy='dynamic')


class flux(db.Model):
  __tablename__ = 'flux'
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(20))
  type = db.Column(db.String(20))
  destination = db.Column(db.String(20))
  operation = db.Column(db.String(20))
  param = db.Column(db.Integer, db.ForeignKey('ports.id'))
  


class harddrive(db.Model):
  __tablename__ = 'harddrive'
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(20))
  type = db.Column(db.String(20))
  capacity = db.Column(db.String(20))
  Content = db.relationship('Content', backref='caches', lazy='dynamic')
  Router_id = db.Column(db.Integer, db.ForeignKey('Router.id'))
     
class Server(db.Model):
  __tablename__ = "Server"
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(20))
  type = db.Column(db.String(20))
  Content = db.relationship('Content', backref='served by', lazy='dynamic') 
  

class Content(db.Model):

  __tablename__ = 'Content'
  id = db.Column(db.Integer, primary_key=True)
  url = db.Column(db.String(20))
  name = db.Column(db.String(20))
  type = db.Column(db.String(20))
  Hits = db.Column(db.Integer)
  prediction = db.Column(db.Integer)
  Server_id = db.Column(db.Integer, db.ForeignKey('Server.id'))
  harddrive_id = db.Column(db.Integer, db.ForeignKey('harddrive.id'))

  def serialize(self):
      return dict(id=self.id,
               url=self.url,
               name=self.name,
               type=self.type,
               Hits=self.Hits,
               Server_id=self.Server_id,
               harddrive_id=self.harddrive_id )


class Cache(db.Model):

  __tablename__ = 'Cache'
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(20))


class visits(db.Model):

  __tablename__ = 'visits'

  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(20))
  date = db.Column(db.DateTime, default=datetime.datetime.utcnow)


# ++++++ File upload to the server  ++++++++++++++++

@app.route('/api/uploads/', methods=['POST','GET'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            return redirect(url_for('upload'))
    return """
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    <p>%s</p>
    """ % "<br>".join(os.listdir(app.config['UPLOAD_FOLDER'],))


# ++++++++++++ File download from the server ++++++++++++++++


@app.route('/api/uploads/<string:file>/', methods=['GET'])
def download(file):

    add_visit(file)
    Increment_Hits(file)
    #sub = db.session.query(func.max(Content.Hits).label('max_hit')).subquery()
    #contenu = db.session.query(Content).join(sub, sub.c.max_hit == Content.Hits).all()
    #name1 = contenu[0].name
    #if name1 == file:
    #   return redirect('http://192.168.198.134:5000%s' % url_for('download',file=file), code=302)
    #else:   
    return send_from_directory(UPLOAD_FOLDER, file)



# ++++++++++ GET the most popular file ++++++++++++++++++++++

@app.route('/API/V1.0/maxhits/', methods=['GET'])

def maxhits():
    sub1 = db.session.query(func.max(Content.Hits).label('max_hit')).subquery()
    contenu1 = db.session.query(Content).join(sub1, sub1.c.max_hit == Content.Hits).first()
    return jsonify(contenu1.serialize()) 


# +++++++++ content caching algorithm ++++++++++++++++ 

@app.route('/api/test/', methods=['GET'])
def catalogue1():
  cache= db.session.query(Cache.name).all()
  Condidat = SortedSet()
  catalogue = db.session.query(Content.name).all()
  k=10
  for i in (catalogue):
    s = WEMA(i)
    if i in cache:
      s = s + k 

    filename=i[0]  
    Condidat.add((s,filename))
    cont = Content.query.filter_by(name=filename).update(dict(prediction=s))
    db.session.commit()
  Condidat1=reversed(Condidat)
  Condidat2= list(Condidat1)
  visits.query.delete()
  Cache.query.delete()  
  for i in Condidat2[0:3]:
    cach = Cache()
    cach.name = i[1]
    db.session.add(cach)
    db.session.commit()
  cache1 = db.session.query(Cache.name).all()
  return make_response(dumps(cache1)) 
     


# +++++  COPY FILES TO CACHE ++++++++++++++++++++
@app.route('/api/copy', methods=['POST','GET'])
def copy():
  catalogue2 = db.session.query(Cache.name).all()

  ssh = paramiko.SSHClient()
  ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  ssh.connect('192.168.198.140', username='cach', password='passwd')
  sftp = ssh.open_sftp()
  for file in catalogue2:
    path1 = 'C:/Users/sony-vaio/Desktop/demo/uploads/%s' % file
    path2 = '/home/loukili/API/uploads/%s' % file
    sftp.put(path1,path2)

  sftp.close()  
  ssh.close()
  return "copied successfully!"





db.create_all()


# +++++++++ API endpoints ++++++++++++++++++++++++++++++

manager = flask.ext.restless.APIManager(app, flask_sqlalchemy_db=db)
manager.create_api(Router, methods=['GET', 'POST', 'DELETE','PUT'])
manager.create_api(ports, include_columns=['id','name','type','status','Router_id'] ,methods=['GET','POST','DELETE','PUT'])
manager.create_api(flux, include_columns=['id','destination','operation','param'] ,methods=['GET','POST','DELETE','PUT'])
manager.create_api(Server, methods=['GET','POST','DELETE','PUT'])
manager.create_api(harddrive, include_columns=['id','name','capacity','type','Router_id' ]  , methods=['GET','POST','PUT','DELETE'])
manager.create_api(Content, methods=['GET','POST','PUT','DELETE','COPY'])
manager.create_api(visits, methods=['GET','POST','DELETE'])
manager.create_api(Cache, methods=['GET','POST','DELETE','PUT'])


if __name__ == '__main__':

  app.run(debug=True)


    



