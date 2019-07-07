import datetime

import firebase_admin
import telebot
from firebase_admin import credentials, firestore

token = '756987925:AAF579YZ_QwxXwAR4dfCM6QSiKGtoS4M-UI'
bot = telebot.TeleBot(token=token)

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': 'facepi1',
})

db = firestore.client()

now = datetime.datetime.now()
today = now.strftime('%d.%m.%Y')
collection_ref = db.collection(today)


def on_snapshot(col_snapshot, changes, read_time):
    for change in changes:
        if change.type.name == 'ADDED':
            value = change.document.reference.get().to_dict()

            if not value:
                continue

            name = value['name']
            department_name = ''
            forbidden = False

            departments = db.collection(u'departments')

            if value['name'] == 'unknown':
                forbidden = True
                doc = departments.document(u'unknown').get().to_dict()
                if doc:
                    tg_id = doc['telegram_id']
                else:
                    return

            else:
                people = db.collection(u'people')
                person = next(people.where(u'name', u'==', name).get(), None).to_dict()

                if person['forbidden']:
                    forbidden = True
                    doc = departments.document(u'forbidden').get().to_dict()
                    if doc:
                        tg_id = doc['telegram_id']
                    else:
                        return

                else:
                    department = next(departments.where(u'name', u'==', person['department']).get(), None).to_dict()
                    department_name = department['name']
                    tg_id = department['telegram_id']

            message_text = name + ' (' + ('forbidden' if forbidden else 'accepted') + ')' + (
                ' from ' + department_name if department_name else '') + ' is there.'
            print(tg_id)
            bot.send_message(tg_id, message_text)


query_watch = collection_ref.on_snapshot(on_snapshot)

while True:
    now = datetime.datetime.now()

    if now == now.replace(hour=0, minute=0, second=1, microsecond=0) or \
            now == now.replace(hour=0, minute=0, second=2, microsecond=0):
        query_watch.unsubscribe()

        now = datetime.datetime.now()
        today = now.strftime('%d.%m.%Y')
        collection_ref = db.collection(today)

        query_watch = collection_ref.on_snapshot(on_snapshot)
