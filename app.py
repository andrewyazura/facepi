import multiprocessing
import os
import shutil

import firebase_admin
from firebase_admin import credentials, firestore
from flask import flash, Flask, redirect, render_template, request
from imutils import paths
from werkzeug.utils import secure_filename

from telegram_bot import send_information
from live_recognition import live_recognition

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg']
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': 'facepi1'
})
db = firestore.client()

is_working = False
live_rec = multiprocessing.Process(target=live_recognition, args=(UPLOAD_FOLDER, db))
telegram_bot = multiprocessing.Process(target=send_information)


def allowed_file(filename):
    return '.' in filename and filename.split('.', 1)[-1].lower() in ALLOWED_EXTENSIONS


def shutdown_func():
    os.system('sudo shutdown now')


def reboot_func():
    os.system('sudo reboot')


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.route('/')
def homepage():
    global is_working
    global live_rec

    if 'start' in request.args:
        is_working = True
        live_rec.start()
        return redirect('/')

    if 'stop' in request.args:
        is_working = False

        if live_rec.is_alive():
            live_rec.terminate()
            live_rec = multiprocessing.Process(target=live_recognition, args=(UPLOAD_FOLDER, db))

        return redirect('/')

    if 'shutdown' in request.args:
        shutdown_proc = multiprocessing.Process(target=shutdown_func)
        shutdown_proc.start()

        return redirect('/')

    if 'reboot' in request.args:
        reboot_proc = multiprocessing.Process(target=reboot_func)
        reboot_proc.start()

        return redirect('/')

    return render_template('index.html', working=is_working)


@app.route('/add_department', methods=['GET', 'POST'])
def add_department():
    if request.method == 'POST':
        department = request.form['department']
        telegram_id = request.form['telegram_id']

        if department == '':
            flash('Enter department name', 'error')
            return redirect('/add_face')

        if len(telegram_id) > 10:
            telegram_id = '-' + telegram_id.split('g')[-1]

        db.collection(u'departments').add({
            u'name':        department,
            u'telegram_id': telegram_id
        })

    departments = db.collection('departments').get()
    departments = [department.to_dict()['name'] for department in departments if
                   department.to_dict()['name'] not in ('unknown', 'forbidden')]

    return render_template('add_department.html', departments=departments)


@app.route('/add_face', methods=['GET', 'POST'])
def upload_face():
    if request.method == 'POST':
        if 'face_image' not in request.files:
            flash('Something went wrong', 'error')
            return redirect('/add_face')

        name = request.form['name']
        department = str(request.form.get('department'))
        file = request.files['face_image']

        if name == '':
            flash('Enter person name', 'error')
            return redirect('/add_face')

        if department == '':
            flash('Enter department', 'error')
            return redirect('/add_face')

        if file.filename == '':
            flash('No file chosen', 'error')
            return redirect('/add_face')

        is_allowed = allowed_file(file.filename)

        if not is_allowed:
            flash('Upload only images', 'error')
            return redirect('/add_face')

        elif file and name and department and is_allowed:
            folder_name = secure_filename(name)

            forbidden = False
            if request.form.get('is_forbidden'):
                forbidden = True

            folder_path = os.path.join(UPLOAD_FOLDER, 'forbidden' if forbidden else '', folder_name)
            filename = secure_filename(file.filename)

            if os.path.exists(folder_path):
                file_path = os.path.join(folder_path, filename)
                file.save(file_path)

            else:
                os.makedirs(folder_path)
                file_path = os.path.join(folder_path, filename)
                file.save(file_path)

            people = db.collection(u'people')
            first_doc = next(people.where(u'name', u'==', folder_name).get(), None)

            if not first_doc:
                people.add({
                    u'name':       folder_name,
                    u'department': department,
                    u'forbidden':  forbidden
                })

            open('.reencode', 'a').close()
            flash('Successfully added face', 'success')
            return redirect('/add_face')

    folders = [(folder, len(os.listdir(os.path.join(UPLOAD_FOLDER, folder)))) for folder in os.listdir(UPLOAD_FOLDER)
               if folder != 'forbidden']
    forbidden_faces = len(os.listdir(os.path.join(UPLOAD_FOLDER, 'forbidden')))
    departments = db.collection('departments').get()
    departments = [department.to_dict()['name'] for department in departments if
                   department.to_dict()['name'] not in ('unknown', 'forbidden')]

    return render_template('add_face.html', folders=folders, forbidden_faces=forbidden_faces, departments=departments)


@app.route('/forbidden_faces')
def show_forbidden():
    forbidden_path = os.path.join(UPLOAD_FOLDER, 'forbidden')
    folders = [(folder, len(os.listdir(os.path.join(forbidden_path, folder)))) for folder in os.listdir(forbidden_path)]

    return render_template('forbidden_faces.html', folders=folders)


@app.route('/photos/<folder_name>')
def see_photos(folder_name):
    photos = list(paths.list_images(os.path.join(UPLOAD_FOLDER, folder_name)))

    return render_template('photos.html', folder_name=folder_name, photos=photos)


@app.route('/forbidden_photos/<folder_name>')
def see_forbidden_photos(folder_name):
    photos = list(paths.list_images(os.path.join(UPLOAD_FOLDER, 'forbidden', folder_name)))

    return render_template('forbidden_photos.html', folder_name=folder_name, photos=photos)


@app.route('/delete_department/<department>')
def delete_department(department):
    department = next(db.collection('departments').where(u'name', u'==', department).get(), None)

    if department:
        department.reference.delete()

        flash('Successfully removed department', 'success')
        return redirect('/add_department')

    flash('Something went wrong', 'error')
    return redirect('/add_department')


@app.route('/delete_folder/<folder_name>')
def delete_folder(folder_name):
    shutil.rmtree(os.path.join(UPLOAD_FOLDER, folder_name))

    first_doc = next(db.collection(u'people').where(u'name', u'==', folder_name).get(), None)
    if first_doc:
        first_doc.reference.delete()

    flash('Successfully removed faces', 'success')
    return redirect('/add_face')


@app.route('/delete_folder/forbidden/<folder_name>')
def delete_forbidden_folder(folder_name):
    shutil.rmtree(os.path.join(UPLOAD_FOLDER, 'forbidden', folder_name))

    first_doc = next(db.collection(u'people').where(u'name', u'==', folder_name).get(), None)
    if first_doc:
        first_doc.reference.delete()

    flash('Successfully removed faces', 'success')
    return redirect('/forbidden_faces')


@app.route('/delete_face/<folder_name>/<file_name>')
def delete_face(folder_name, file_name):
    os.remove(os.path.join(UPLOAD_FOLDER, folder_name, file_name))

    flash('Successfully removed face', 'success')
    return redirect('/add_face')


@app.route('/delete_face/forbidden/<folder_name>/<file_name>')
def delete_forbidden_face(folder_name, file_name):
    os.remove(os.path.join(UPLOAD_FOLDER, 'forbidden', folder_name, file_name))

    flash('Successfully removed face', 'success')
    return redirect('/forbidden_faces')


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        telegram_id = request.form['telegram_id']

        if not telegram_id:
            flash('Login with Telegram to continue', 'error')
            return redirect('/settings')

        departments = db.collection(u'departments')
        departments.document(u'unknown').set({
            u'name':        u'unknown',
            u'telegram_id': telegram_id
        })
        departments.document(u'forbidden').set({
            u'name':        u'forbidden',
            u'telegram_id': telegram_id
        })

        flash('Successfully logged in', 'success')
        return redirect('/settings')

    return render_template('settings.html')


@app.route('/tutorials')
def tutorials():
    return render_template('tutorials.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
    telegram_bot.start()
