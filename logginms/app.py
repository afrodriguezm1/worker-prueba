from flask import Flask, app, request
from flask_cors import CORS
from util import FileManager

app = Flask(__name__)

fileManager = FileManager.get_instance()

app.config['PROPAGATE_EXCEPTIONS'] = True
app_context = app.app_context()
app_context.push()
cors = CORS(app)

@app.route('/logTransaction', methods=['POST'])
def post():
    taskId = request.json["taskId"]
    timecreated = request.json["timecreated"]
    timestart = request.json["timestart"]
    diff = request.json["diff"]
    timeend = request.json["timeend"]
    file = open('./Files/loglectura.txt', 'a')
    file.write("{},{},{},{},{}\n".format(taskId,timecreated, timestart, diff, timeend))
    file.close()
    return "Entry logged", 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')