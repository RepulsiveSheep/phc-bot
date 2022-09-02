import threading
import sys

from flask import Flask

from phc_bot.app import process_submissions, process_mentions

app = Flask(__name__)

submissions_thread = threading.Thread(target=process_submissions)
mentions_thread = threading.Thread(target=process_mentions)


@app.route('/')
def run():
    global submissions_thread, mentions_thread

    if not submissions_thread.is_alive():
        submissions_thread = threading.Thread(target=process_submissions)
        submissions_thread.start()

    if not mentions_thread.is_alive():
        mentions_thread = threading.Thread(target=process_mentions)
        mentions_thread.start()
    return 'thy has been done'


@app.route('/hello')
def hello():
    return 'why are you?'
