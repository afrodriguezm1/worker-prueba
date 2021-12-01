from flask import Flask
from flask_restful import Api
from vistas import VistaTasks, VistaUpdateTask, VistaGetFiles, VistaTask, VistaHealthCheck
from modelos import db
from flask_jwt_extended import JWTManager
import os

app = Flask(__name__)

dbHost = os.environ.get("DB_HOST")
dbNameGestorTareas = os.environ.get("DB_NAME_GESTORTAREAS")
dbUser = os.environ.get("DB_USER")
dbPassword = os.environ.get("DB_PASSWORD")

environment = os.environ.get("PROJECT_ENVIRONMENT")
if environment == "develop":
    app.config['SQL_ALCHEMY_DATABASE_URI'] = 'sqlite:///gestor-tareas.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{dbUser}:{dbPassword}@{dbHost}/{dbNameGestorTareas}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ["JWT_SECRET_KEY"]
app.config['PROPAGATE_EXCEPTIONS'] = True
app_context = app.app_context()
app_context.push()

db.init_app(app)
db.create_all()

api = Api(app)
api.add_resource(VistaHealthCheck, '/healthCheck')
api.add_resource(VistaTasks, '/tasks')
api.add_resource(VistaTask, '/tasks/<int:id_task>')
api.add_resource(VistaUpdateTask, '/updateTask')
api.add_resource(VistaGetFiles, '/tasks/<filename>')

jwt = JWTManager(app)
