import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from threading import Thread
import socket
import base64
from flask_cors import CORS, cross_origin


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
# Initialize empty user list and chat log
CORS(app)
users = []
chat_log = []

# Set up TCP socket for file/image transfer
TCP_IP = 'localhost'
TCP_PORT = 5005
BUFFER_SIZE = 1024

def send_file(filename, conn):
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'rb') as f:
        while True:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            conn.send(data)
    conn.close()

def receive_file(filename, conn):
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'wb') as f:
        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            f.write(data)
    conn.close()

@app.route('/', methods=['GET', 'POST'])

def index():
    if request.method == 'POST':
        username = request.form['username']
        if username:
            users.append(username)
            return redirect(url_for('chat', username=username))
    return render_template('login.html')

@app.route('/chat')
def chat():
    username = request.args.get('username')
    if username not in users:
        return redirect(url_for('index'))
    return render_template('chat.html', username=username, users=users, chat_log=chat_log)

@app.route('/send_message', methods=['POST'])
def send_message():
    username = request.form['username']
    message = request.form['message']
    if username and message:
        chat_log.append(f'{username}: {message}')
        return 'OK'
    return 'Bad Request', 400

@app.route('/send_file', methods=['POST'])
def send_file_route():
    username = request.form['username']
    file = request.files['file']
    if username and file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # Start new thread to send file over TCP socket
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((TCP_IP, TCP_PORT))
        Thread(target=send_file, args=(filename, conn)).start()
        return 'OK'
    return 'Bad Request', 400

@app.route('/send_image', methods=['POST'])
def send_image():
    username = request.form['username']
    image = request.files['image']
    if username and image:
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'rb') as f:
            image_data = base64.b64encode(f.read())
        return image_data
    return 'Bad Request', 400

@app.route('/download_center')
def download_center():
    files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            files.append({'filename': filename, 'type': 'file'})
        elif os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            files.append({'filename': filename, 'type': 'folder'})
    return render_template('download.html', files=files)

@app.route('/download_file/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # Start TCP server for file/image transfer
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        Thread(target=receive_file, args=(conn.recv(BUFFER_SIZE).decode(), conn)).start()
        app.run(debug=True,ssl_context='adhoc')