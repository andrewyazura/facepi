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
    if not os.path.exists('.reencode'):
        print('[INFO] no need to re-encode faces, skipping')
        return

    print('[INFO] quantifying faces...')
    image_paths = list(paths.list_images(folder_path))
    known_encodings = []
    known_names = []

    detector = cv2.CascadeClassifier('/home/pi/facepi/live_recognition/haarcascade_frontalface_default.xml')

    for (i, image_path) in enumerate(image_paths):
        print('[INFO] processing image {}/{}'.format(i + 1, len(image_paths)))
        name = image_path.split(os.path.sep)[-2]

        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        rects = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(90, 90))
        boxes = [(y, x + w, y + h, x) for (x, y, w, h) in rects]
        encodings = face_recognition.face_encodings(rgb, boxes)

        print('[INFO] found', len(encodings), 'faces')
        for encoding in encodings:
            known_encodings.append(encoding)
            known_names.append(name)

    print('[INFO] saving encodings...')
    data = {'encodings': known_encodings, 'names': known_names}
    f = open('encodings', 'wb')
    f.write(pickle.dumps(data))
    f.close()
    os.remove('.reencode')


def live_recognition(images_folder, db):
    save_encodings(images_folder)

    print('[INFO] loading encodings + face detector...')
    data = pickle.loads(open('encodings', 'rb').read())
    detector = cv2.CascadeClassifier('/home/pi/facepi/live_recognition/haarcascade_frontalface_default.xml')

    print('[INFO] starting video stream...')
    vs = VideoStream(usePiCamera=True).start()
    time.sleep(2.0)

    print('[INFO] contacting database')
    # cred = credentials.ApplicationDefault()
    # firebase_admin.initialize_app(cred, {
    #     'projectId': 'facepi1'
    # })
    # db = firestore.client()

    now = datetime.datetime.now()
    today = now.strftime('%d.%m.%Y')
    collection_ref = db.collection(u'collection_dates')
    first_doc = next(collection_ref.where(u'name', u'==', today).get(), None)

    if not first_doc:
        collection_ref.add({
            u'name': today
        })

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
                                          minNeighbors=5, minSize=(60, 60),
                                          flags=cv2.CASCADE_SCALE_IMAGE)

        boxes = [(y, x + w, y + h, x) for (x, y, w, h) in rects]

        encodings = face_recognition.face_encodings(rgb, boxes)
        names = []

        now = datetime.datetime.now()
        today = now.strftime('%d.%m.%Y')
        collection_ref = db.collection(today)

        if now == now.replace(hour=0, minute=0, second=2, microsecond=0):
            db.collection(u'collection_dates').add({
                u'name': today
            })

        for encoding in encodings:
            matches = face_recognition.compare_faces(data['encodings'], encoding)

            if True in matches:
                matched = [i for (i, b) in enumerate(matches) if b]
                counts = {}

                for i in matched:
                    counts[i] = counts.get(i, 0) + 1

                index = max(counts, key=counts.get)
                name = data['names'][index]
                names.append(name)

                print('[INFO]', name)

            if all(match == False for match in matches):
                print('[INFO] unknown person')
                time_from_unknown = abs((now - last_unknown).total_seconds())

                if time_from_unknown >= 10:
                    # cv2.imwrite('static/unknown/', frame)
                    last_unknown = now
                    collection_ref.add({
                        u'name':     u'unknown',
                        u'datetime': now
                    })

        for name in names:
            time_from_last = abs((now - last_visits.get(name, datetime.datetime(1970, 1, 1))).total_seconds())

            if time_from_last >= 10:
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
