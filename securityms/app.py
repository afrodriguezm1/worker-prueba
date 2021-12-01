from flask import Flask, app, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from flask_cors import CORS
from flask_jwt_extended.utils import get_jwt, get_jwt_identity
from flask_jwt_extended import JWTManager, create_access_token, jwt_required

from flask_sqlalchemy import SQLAlchemy
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import os
import datetime

app = Flask(__name__)

dbHost = os.environ.get("DB_HOST")
dbNameSecurityms = os.environ.get("DB_NAME_SECURITYMS")
dbUser = os.environ.get("DB_USER")
dbPassword = os.environ.get("DB_PASSWORD")

app.logger.info(dbHost)

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{dbUser}:{dbPassword}@{dbHost}/{dbNameSecurityms}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ["JWT_SECRET_KEY"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=24)
app.config['PROPAGATE_EXCEPTIONS'] = True

app_context = app.app_context()
app_context.push()
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    password = db.Column(db.String(50))
    password2 = db.Column(db.String(50))
    email = db.Column(db.String(50))


class UsuarioSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        exclude = ('password', 'password2')
        include_relationships = True
        load_instance = True


db.init_app(app)
db.create_all()

cors = CORS(app)
jwt = JWTManager(app)

usuario_schema = UsuarioSchema()


@app.route('/signup', methods=['POST'])
def post():
    new_user = User(username=request.json["username"], password=request.json["password"],
                    password2=request.json["password2"], email=request.json["email"])
    user = User.query.filter(User.email == new_user.email).first()
    if user is None:
        if new_user.password == new_user.password2:
            db.session.add(new_user)
            db.session.commit()
            additional_claims = {"email": new_user.email}
            access_token = create_access_token(identity={"id": new_user.id, "email": new_user.email},
                                               additional_claims=additional_claims)
            db.session.close()
            return {"message": "User created sucessfully", "token": access_token}
        else:
            db.session.close()
            return {"message": "Password and password2 fields doesn't match, please correct it and try again"}
    else:
        email = new_user.email
        db.session.close()
        return {"message": "User with email {} is already created".format(email)}


@app.route('/login', methods=['POST'])
def postAuth():
    user = User.query.filter(
        User.username == request.json["username"] and User.password == request.json["password"]).first()
    db.session.commit()
    if user is None:
        return "User doesn't exists", 404
    else:
        additional_claims = {"email": user.email}
        access_token = create_access_token(identity={"id": user.id, "email": user.email},
                                           additional_claims=additional_claims)
        userDump = usuario_schema.dump(user)
        db.session.close()
        return {"message": "Sucessfull login", "token": access_token, "user": userDump}


@app.route('/validate', methods=['GET'])
@jwt_required()
def get():
    jwtHeader = get_jwt()
    identity = get_jwt_identity()
    if ((jwtHeader["email"] == "") or (identity is None)):
        return "The user is not authorized to access to the resource", 403

    return jwtHeader, 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
