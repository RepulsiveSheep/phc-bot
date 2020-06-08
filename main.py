import threading

from flask import Flask

from app import process_submissions, process_mentions

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
