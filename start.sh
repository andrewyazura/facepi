#!/bin/bash -
cd /home/pi/facepi
source OpenCV-master-py3/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS="facepicreds.json"
python app.py & python telegram_bot/main.py
