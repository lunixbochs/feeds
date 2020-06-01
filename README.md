# feeds

This project transcribes audio feeds with speech recognition software. It has a frontend in which people can look at the transcriptions and suggest improvements.

## Setup

To keep your system python clean, usage of a venv is helpful

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Generate the config with

```sh
cd server
python3 gencfg.py > config.cfg
```

You need a MongoDB running on the default port of `27017`. If you don’t want it in your system, you may use docker:

```sh
docker run --rm -d -p 127.0.0.1:27017:27017 --name mongodb-feeds mongo:4.2.7-bionic
```

Run it with

```sh
FLASK_SETTINGS=config.cfg python3 run.py
```
