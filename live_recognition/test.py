import datetime
import os
import pickle
import time

import cv2
import face_recognition
import firebase_admin
import imutils
from firebase_admin import credentials, firestore
from imutils import paths
from imutils.video import VideoStream


def save_encodings(folder_path):
    print('[INFO] quantifying faces...')
    image_paths = list(paths.list_images(folder_path))
    known_encodings = []
    known_names = []

    detector = cv2.CascadeClassifier('/home/pi/facepi/live_recognition/haarcascade_frontalface_default.xml')

    for (i, image_path) in enumerate(image_paths):
        print('[INFO] processing image {}/{}'.format(i + 1, len(image_paths)))
        name = image_path.split(os.path.sep)[-2].split('.')[0]

        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        rects = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        boxes = [(y, x + w, y + h, x) for (x, y, w, h) in rects]
        encodings = face_recognition.face_encodings(rgb, boxes)

        for encoding in encodings:
            known_encodings.append(encoding)
            known_names.append(name)

    print('[INFO] saving encodings...')
    data = {'encodings': known_encodings, 'names': known_names}
    f = open('encodings', 'wb')
    f.write(pickle.dumps(data))
    f.close()


def live_recognition(images_folder):
    save_encodings(images_folder)

    print('[INFO] loading encodings + face detector...')
    data = pickle.loads(open('encodings', 'rb').read())
    detector = cv2.CascadeClassifier('/home/pi/facepi/live_recognition/haarcascade_frontalface_default.xml')

    print('[INFO] starting video stream...')
    vs = VideoStream(usePiCamera=True).start()
    time.sleep(2.0)

    print('[INFO] contacting database')
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'projectId': 'facepi1'
    })
    db = firestore.client()

    print('[INFO] getting collection')
    today = datetime.date.today()
    today = today.strftime('%d.%m.%Y')
    collection_ref = db.collection(today)

    print('[INFO] preparing')
    last_unknown = datetime.datetime(1970, 1, 1)
    last_visits = {}

    print('[INFO] started')
    while True:
        frame = vs.read()
        frame = imutils.resize(frame, width=800)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        rects = detector.detectMultiScale(gray, scaleFactor=1.2,
                                          minNeighbors=5, minSize=(50, 50),
                                          flags=cv2.CASCADE_SCALE_IMAGE)

        boxes = [(y, x + w, y + h, x) for (x, y, w, h) in rects]

        encodings = face_recognition.face_encodings(rgb, boxes)
        names = []

        for encoding in encodings:
            matches = face_recognition.compare_faces(data['encodings'], encoding)

            if True in matches:
                matched = [i for (i, b) in enumerate(matches) if b]
                counts = {}

                for i in matched:
                    name = data['names'][i]
                    counts[name] = counts.get(name, 0) + 1

                name = max(counts, key=counts.get)
                names.append(name)
                print('[INFO]', name)

            if all(match is False for match in matches):
                print('[INFO] unknown person')

                now = datetime.datetime.now()
                time_from_unknown = abs((now - last_unknown).total_seconds())

                if time_from_unknown >= 5:
                    last_unknown = now
                    collection_ref.add({
                        u'name':     'Unknown',
                        u'datetime': now
                    })

        now = datetime.datetime.now()
        for name in names:
            time_from_last = abs((now - last_visits.get(name, datetime.datetime(1970, 1, 1))).total_seconds())

            if time_from_last >= 5:
                last_visits[name] = now
                collection_ref.add({
                    u'name':     name,
                    u'datetime': now
                })

        # cv2.imshow("Frame", frame)
        # key = cv2.waitKey(1) & 0xFF


if __name__ == '__main__':
    print('Starting')
    live_recognition('/home/pi/facepi/static/uploads/')
    print('Ended')
