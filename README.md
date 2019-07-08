# Face Pi
Face Pi is security system with facial recognition that notifies about people it sees

> **Note:** Face Pi works only on Raspberry Pi. Supported OS: Raspbian Stretch. Planning to move to Raspbian Buster.

## List of source files:

##### `live_recognition/__init__.py` - facial recognition module

##### `static/scripts/*` - JavaScript scripts for web-page

##### `static/styles/*` - CSS files for web-page

##### `telegram_bot/main.py` - Telegram bot for notifying users

##### `templates/*` - templates for web-page

##### `app.py` - Flask server for web-page

##### `facepicreds.json` - credentials for Firestore database

##### `install-opencv.sh` - script for installing OpenCV 4 on Raspberry Pi

##### `requirements.txt` - all project dependencies

##### `start.sh` - script for starting the whole project

## How to start the project:

1. Create folder `facepi` in `/home/pi/`
    1. `mkdir /home/pi/facepi`
2. Put all project files into `/home/pi/facepi`
3. Go to `/home/pi/facepi`
    1. `cd /home/pi/facepi`
4. Run `install-opencv.sh`
    1. `sudo chmod +x install-opencv.sh`
    2. `sudo ./install-opencv.sh`
    3. This can take up to 9 hours
5. Install other requirements in VirtualEnv created before when installing OpenCV
    1. `source /OpenCV-master-py3/bin/activate`
    2. `pip install -r requirements.txt`
    3. `deactivate`
6. Run `start.sh`
    1. `sudo chmod +x start.sh`
    2. `sudo ./start.sh`

_If something goes wrong, contact me on Gmail: `andrewyazura203@gmail.com` or Telegram: `@python390`_
