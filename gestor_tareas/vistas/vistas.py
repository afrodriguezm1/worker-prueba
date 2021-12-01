import json

from flask import request, send_file
from flask_restful import Resource
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_jwt_extended.utils import get_jwt
from modelos import db, Task, TaskSchema, Status
from celery import Celery
import os
import time
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from util import FileManager, AwsS3

task_schema = TaskSchema()
tasks_schema = TaskSchema(many=True)

smtp_enable = os.environ.get('SMTP_enable', False)
smtp_server = os.environ["SMTP_EMAIL_SERVER"]
smt_port = int(os.environ["SMTP_EMAIL_PORT"])
sender_email = os.environ["SMTP_EMAIL_SENDER_EMAIL"]
password = os.environ["SMTP_EMAIL_SENDER_PASSWORD"]

queue_url = os.environ["SQS_QUEUE_URL"]
queue_name = os.environ["SQS_QUEUE_NAME"]

celery_app = Celery('gestor',
                    broker=f"sqs://{queue_url}",
                    backend='rpc://',
                    task_default_queue=f"{queue_name}")

fileManager = FileManager.get_instance()

def get_target_name(task):
    return os.path.splitext(task.filename)[0] + '.' + task.newFormat.name.lower()

class VistaHealthCheck(Resource):
    def get(self):
        return 200

class VistaTasks(Resource):
    @jwt_required()
    def get(self):
        jwtHeader = get_jwt()
        tasks = Task.query.filter(Task.userEmail == jwtHeader["email"])
        tasksDump = tasks_schema.dump(tasks, many=True)
        db.session.close()
        return {"tasks": tasksDump}, 200

    @jwt_required()
    def post(self):
        # Get user data
        userIdentity = get_jwt_identity()
        userEmail = userIdentity["email"]
        userId = userIdentity["id"]
        tiempo = round(time.time())
        file = request.files['file']
        try:
            fileManager.save_file(file, file.filename, userId)
            nueva_task = Task(filename=file.filename,
                              newFormat=request.form.get("newFormat"),
                              timeCreated=tiempo,
                              status="UPLOADED",
                              userEmail=userEmail)
            db.session.add(nueva_task)
            db.session.commit()
            r = celery_app.send_task('tasks.convert_task',
                                     kwargs={
                                         'filename': file.filename,
                                         "newFormat": request.form.get("newFormat"),
                                         "userId": userId,
                                         "taskId": nueva_task.id,
                                         "timecreated": tiempo})
            taskDump = task_schema.dump(nueva_task)
            db.session.close()
            return {"task": taskDump, "cola": r.id}, 200
        except Exception:
            db.session.rollback()
            db.session.close()
            return "Ocurrió un error al guardar el archivo", 500


def remove_file(filename, userid):
    try:
        fileManager.delete_file(filename, userid)
        return "OK"
    except PermissionError:
        return "You do not have permission to delete that"
    except FileNotFoundError:
        return "The file does not exist"
    except OSError:
        return "File path can not be removed"


class VistaGetFiles(Resource):
    @jwt_required()
    def get(self, filename):
        userIdentity = get_jwt_identity()
        userId = userIdentity["id"]
        try:
            response = fileManager.return_file(filename, userId)
        except:
            return "Archivo no encontrado", 404

        if type(fileManager) is AwsS3:
            return json.dumps({'urlfile': response})
        else:
            file = send_file(f"{response}", mimetype=str(filename)[-3:], attachment_filename=f"{filename}",
                             as_attachment=True)
            return file


class VistaTask(Resource):
    @jwt_required()
    def get(self, id_task):
        jwtHeader = get_jwt()
        task = Task.query.filter_by(id=id_task, userEmail=jwtHeader["email"])
        if task is None:
            return None, 404
        taskDump = tasks_schema.dump(task)
        db.session.close()
        return taskDump, 200

    @jwt_required()
    def put(self, id_task):
        # Get user data
        tiempo = round(time.time())
        userIdentity = get_jwt_identity()
        userEmail = userIdentity["email"]
        userId = userIdentity["id"]

        task = Task.query.filter_by(id=id_task, userEmail=userEmail).first()
        if task is None:
            return None, 404

        newFormat = request.json.get("newFormat")
        oldTarget = get_target_name(task)
        task.newFormat = newFormat  # Actualiza el formato de la tarea

        if task.status == Status.PROCESSED:
            remove_file(oldTarget, userId)
            task.status = Status.UPLOADED

        try:
            db.session.commit()
        except:
            db.session.rollback()
            db.session.close()
            return "Ocurrió un error al actualizar el formato", 500

        r = celery_app.send_task('tasks.convert_task',
                                 kwargs={
                                     'filename': task.filename,
                                     "newFormat": newFormat,
                                     "userId": userId,
                                     "taskId": task.id,
                                     "timecreated": tiempo})
        taskDump = tasks_schema.dump([task])
        db.session.close()
        return taskDump, 200

    @jwt_required()
    def delete(self, id_task):
        # Get user data
        userIdentity = get_jwt_identity()
        userEmail = userIdentity["email"]
        userId = userIdentity["id"]

        task = Task.query.filter_by(id=id_task, userEmail=userEmail).first()
        if task is None:
            db.session.close()
            return None, 404

        if task.status != Status.PROCESSED:
            return "The task is not processed", 500

        fileoriginal = task.filename
        fileprocessed = os.path.splitext(task.filename)[0] + '.' + task.newFormat.name.lower()
        response = remove_file(fileoriginal, userId)
        if response != "OK":
            db.session.close()
            return response, 500

        response = remove_file(fileprocessed, userId)
        if response != "OK":
            db.session.close()
            return response, 500

        Task.query.filter_by(id=id_task, userEmail=userEmail).delete()
        try:
            db.session.commit()
        except:
            db.session.rollback()
            db.session.close()
            return "Ocurrió un error al eliminar la tarea", 500

        db.session.close()
        return 'Tarea eliminada', 200


class VistaUpdateTask(Resource):
    def post(self):
        task = Task.query.get_or_404(request.json["taskId"])
        task.status = "PROCESSED"
        try:
            db.session.commit()
        except:
            db.session.rollback()
            db.session.close()
            return "Ocurrió un error al actualizar el estado de la tarea", 500

        if not smtp_enable:
            return 'email deshabilitado', 200

        message = MIMEMultipart("alternative")
        message["Subject"] = "Archivo procesado"
        message["From"] = sender_email
        message["To"] = task.userEmail

        newFile = task.filename[:-3] + str(task.newFormat)[-3:]

        text = f"""\
            Tu archivo está listo
            Hola,
            Nos alegra informarte que tu archivo {task.filename} se convirtió exitosamente.
            Para descargar tu archivo accede a la aplicación y solicita el archivo {newFile}.
            Grácias por preferirnos - Grupo 18"""

        html = f"""\
            <html>
                <body>
                    <h2>Tu archivo está listo</h2>
                        <p>
                            Hola...<br>
                            Nos alegra informarte que tu archivo <b>{task.filename}</b> se convirtió exitosamente.<br>
                            Para descargar tu archivo accede a la aplicación y solicita el archivo <b>{newFile}</b>.<br><br>
                            <i>Grácias por preferirnos - Grupo 18</i>
                        </p>
                    </body>
                </html>
            """

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        message.attach(part1)
        message.attach(part2)

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, smt_port, context=context) as server:
                server.login(sender_email, password)
                server.sendmail(
                    sender_email, task.userEmail, message.as_string()
                )
                server.quit()
        except Exception as e:
            print(e)
        finally:
            db.session.close()
        return 'email enviado', 200
