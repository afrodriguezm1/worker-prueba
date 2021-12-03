import time
from celery import Celery
from celery.utils.log import get_task_logger
import requests
from pydub import AudioSegment
import os
from util import FileManager

logger = get_task_logger(__name__)

gestor_tareas_host = os.environ.get("GESTOR_TAREAS_HOST")
log_host = os.environ.get("LOG_HOST")

celery_conect = os.environ.get("CELERY_CONECT")

if(celery_conect == "rabbit-ec2"):

    rabbit_user = os.environ.get("RABBITMQ_DEFAULT_USER")
    rabbit_password = os.environ.get("RABBITMQ_DEFAULT_PASS")
    rabbit_hostname = os.environ.get("RABBITMQ_HOSTNAME")

    print(rabbit_user, rabbit_password, rabbit_hostname)

    app = Celery('tasks',
             broker=f"amqp://{rabbit_user}:{rabbit_password}@{rabbit_hostname}:5672",
             backend='rpc://')

elif (celery_conect == "rabbit-heroku"):

    rabbit_url = os.environ.get("RABBIT_URL")

    app = Celery('tasks',
             broker=f"{rabbit_url}",
             backend='rpc://')
             
elif (celery_conect == "sqs"):
    
    queue_url = os.environ.get("SQS_QUEUE_URL")
    queue_name = os.environ.get("SQS_QUEUE_NAME")

    app = Celery('tasks',
             broker=f"sqs://{queue_url}",
             backend='rpc://',
             task_default_queue=f'{queue_name}')

fileManager = FileManager.get_instance()


@app.task()
def convert_task(filename, newFormat, userId, taskId, timecreated):
    timestart = round(time.time())
    diff = timestart - timecreated
    logger.info(f'Solicitud de conversión - {filename} a {newFormat}')
    resp = convert_validation(filename, newFormat, userId)
    timeend = round(time.time())
    #requests.post(f"{log_host}/logTransaction", json={"taskId": taskId,"timecreated": timecreated,"timestart": timestart,"diff": diff,"timeend": timeend})
    if resp:
        logger.info(f"Conversión de archvio {filename} a {newFormat}")
        requests.post(f"{gestor_tareas_host}/updateTask",json={"taskId": taskId})


def convert_validation(filename, newFormat, userId):
    filenameSplit = filename.split(".")
    extencion = filenameSplit[len(filenameSplit) - 1]
    if extencion in ['mp3', 'aac', 'wav', 'wma', 'ogg']:
        return audio_convert(filename, newFormat, userId)
    else:
        logger.info(f'El archivo con extención {extencion} no es soportado')
        return False


def audio_convert(filename, newFormat, userId):
    filenameSplit = filename.split(".")
    extencion = filenameSplit[len(filenameSplit) - 1]
    # f"./Files/{userId}/{filename}"
    source_path = fileManager.get_file(filename, userId)

    target_name = filename[:-3] + newFormat
    destination_path = f"./Files/{userId}/" + target_name
    try:
        if extencion == "mp3":
            AudioSegment.from_mp3(source_path).export(
                destination_path, format=newFormat)
        elif extencion == "ogg":
            AudioSegment.from_ogg(source_path).export(
                destination_path, format=newFormat)
        elif extencion == "wav":
            AudioSegment.from_wav(source_path).export(
                destination_path, format=newFormat)
        else:
            AudioSegment.from_file(source_path).export(
                destination_path, format=newFormat)
    except:
        fileManager.clean_local_files(userId)
        return False

    fileManager.send_file(destination_path, target_name, userId)
    return True
