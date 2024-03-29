#!/usr/bin/env python3

import logging
import os
import secrets
import time
import urllib.request
from typing import Optional, Union, Iterable
from urllib.error import HTTPError
from urllib.parse import urlparse, urlunparse, quote

import lxml.html as lh
import magic
import praw
import pytesseract
import requests
from dotenv import load_dotenv
from googlesearch import search as google_search
from praw import Reddit
from praw.models import Submission, Comment

from phc_bot.db import RepliedSubmission, RepliedComment

load_dotenv()

DEBUG_MODE = os.getenv('DEBUG') == '1'

mylogger = logging.getLogger(__name__)
mylogger.addHandler(logging.StreamHandler())
if DEBUG_MODE:
    mylogger.setLevel(logging.DEBUG)
else:
    mylogger.setLevel(logging.WARNING)

UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0',
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.141 Safari/537.36',
      'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.141 Safari/537.36',
      'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.141 Safari/537.36',
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.141 Safari/537.36')

SUBREDDIT = os.getenv('REDDIT_SUBREDDIT')

MAINTAINER = os.getenv('REDDIT_BOT_MAINTAINER')

USERNAME = os.getenv('REDDIT_USERNAME')
PASSWORD = os.getenv('REDDIT_PASSWORD')

CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')

INFO_PAGE_LINK = 'https://www.reddit.com/user/phc-bot/comments/gc0nv6/info/'
SOURCE_CODE_LINK = 'https://github.com/RepulsiveSheep/phc-bot'
SHUTTING_DOWN_LINK = 'https://www.reddit.com/user/RepulsiveSheep/comments/x4aboi/shutting_down_phcbot/'
SAUCE_NOT_FOUND_MESSAGE = '''Sorry! I couldn't find the sauce for this one :('''
OTHER_SUB_DISCLAIMER = ('''Beep boop, I'm a bot! I try to find the PornHub video from a screenshot of PornHub '''
                        '''comments or video title.''')


class Prediction:

    def __init__(self, link, ocr_text, query_text):
        self.link = link
        self.ocr_text = ocr_text
        self.query_text = query_text

    def __repr__(self):
        return f'<Prediction(link={self.link!r})>'

    # noinspection PyProtectedMember
    def link_with_text_highlighted(self):
        url_parsed = urlparse(self.link)
        url_parsed = url_parsed._replace(fragment=url_parsed.fragment + f':~:text={quote(self.query_text)}')
        return urlunparse(url_parsed)

    @staticmethod
    def from_replied_submission(replied_submission: RepliedSubmission):
        return Prediction(link=replied_submission.predicted_link, ocr_text=replied_submission.ocr_text,
                          query_text=replied_submission.query_text)


# noinspection PyBroadException
def search(query: str) -> tuple:
    query = f'site:pornhub.com/view_video.php "{query}"'
    mylogger.debug(f'Searching for query {query!r} via Google...')

    try:
        results = list(google_search(query, stop=1, user_agent=secrets.choice(UA)))
    except Exception as e:
        mylogger.error(f'Google search failed, trying duck: {e!r}')
        mylogger.debug(f'Query that failed: {query}')
        results = duck_search(query)
    time.sleep(5)
    return clean_ph_links(results[:1])


def duck_search(query):
    headers = {
        'authority': 'duckduckgo.com',
        'cache-control': 'max-age=0',
        'origin': 'https://duckduckgo.com',
        'upgrade-insecure-requests': '1',
        'dnt': '1',
        'content-type': 'application/x-www-form-urlencoded',
        'user-agent': secrets.choice(UA),
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'referer': 'https://duckduckgo.com/',
        'accept-language': 'en-US,q=0.9,en-US;q=0.8,en;q=0.7',
    }

    data = {
        'q': query,
        'b': '',
    }

    res = requests.post('https://duckduckgo.com/html/', headers=headers, data=data)
    if not res.ok:
        raise Exception(f'Duck search failed: ({res.status_code}): {res.text}')

    root = lh.fromstring(res.text)
    link_nodes = root.cssselect('#links .result .result__a')
    return [a.get('href', None) for a in link_nodes if a.get('href', None)]


# noinspection PyProtectedMember
def clean_ph_links(links: Iterable[str]) -> tuple:
    clean_links = []
    for link in links:
        url_parsed = urlparse(link)
        if not url_parsed:
            continue

        hostname = url_parsed.netloc
        if hostname != 'pornhub.com' and not hostname.endswith('.pornhub.com'):
            continue

        url_parsed = url_parsed._replace(netloc='www.pornhub.com')
        clean_links.append(urlunparse(url_parsed))

    return tuple(clean_links)


def get_string_to_search(string: str) -> str:
    lines = string.splitlines()
    blacklisted_phrases = [
        'year ago', 'month ago', 'week ago', 'day ago', 'hour ago',
        'years ago', 'months ago', 'weeks ago', 'days ago', 'hours ago',
        'Reply', 'VIEW ALL REPLIES', 'AT&T'
    ]
    final_lines = []
    for line in lines:
        if any(w in line for w in blacklisted_phrases):
            continue
        line = line.replace('|', 'I')
        line = line.replace('"', '')
        line = line.replace('’', "'")
        final_lines.append(line)

    output = '\n'.join(final_lines)
    other_lines = output.split('\n\n')
    other_lines = [line.replace('\n', ' ') for line in other_lines]
    return max(other_lines, key=len).strip()


def get_ph_title(url):
    title = None
    try:
        res = requests.get(url)
        if res.ok:
            root = lh.fromstring(res.text)
            title_nodes = root.cssselect('title')
            title: Optional[str] = (len(title_nodes) and title_nodes[0].text) or None
    except Exception as e:
        print(f'{e!r}')
    return title


def escape_reddit_link_text(text: str) -> str:
    escape_chars = ('[', ']', '*', '_')
    for ch in escape_chars:
        text = text.replace(ch, rf'\{ch}')
    return text


def reply_with_sauce(comment: Union[Submission, Comment], predicted_link, title) -> Optional[Comment]:
    other_sub_disclaimer = ''
    if isinstance(comment, Comment):
        if comment.submission.subreddit.display_name != SUBREDDIT:
            other_sub_disclaimer = f'{OTHER_SUB_DISCLAIMER} Here\'s what I found for this one.\n\n'

    if title:
        sauce_line = f'Sauce (**NSFW**): [{escape_reddit_link_text(title)}]({predicted_link})'
    else:
        sauce_line = f'[Sauce (**NSFW**)]({predicted_link})'
    return comment.reply(
        f'{other_sub_disclaimer}'
        f'{sauce_line}\n\n'
        '---\n\n'
        '*I am a bot, and while I\'m not always right, I try my very best.*\n\n'
        f'[How?]({INFO_PAGE_LINK}) | [Sauce code]({SOURCE_CODE_LINK}) | [Shutting down soon]({SHUTTING_DOWN_LINK})',
    )


def get_prediction(submission: Submission) -> Optional[Prediction]:
    if submission.is_self or not submission.url:
        mylogger.debug(f'URL not found for submission {submission.id!r} returning None as prediction...')
        return None

    mylogger.debug(f'Parsing URL to get prediction for submission {submission.id!r}...')
    url = submission.url
    url_parsed = urlparse(url)
    # TODO: handle imgur.com/a/abc.jpg case (gallery)
    if url_parsed.netloc == 'imgur.com' and '.' not in url_parsed.path:
        mylogger.debug(
            f'Submission link of type imgur.com/abc found for submission {submission.id!r}, original link {submission.url!r}, appending .jpg')
        url = f'https://i.imgur.com{url_parsed.path}.jpg'

    filename = os.path.basename(url)
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    filepath = os.path.join(curr_dir, 'images', filename)
    mylogger.debug(f'Saving {url!r} to {filepath!r} for submission {submission.id!r}, URL {submission.url!r}...')
    try:
        urllib.request.urlretrieve(url, filepath)
    except HTTPError as e:
        mylogger.error(f'Could not retrieve {url!r} for submission {submission.id!r}, HTTPError: {e!r}')
        return None

    mylogger.debug(f'Saved successfully to {filepath!r}! Getting mime type')
    mime = magic.from_file(filepath, mime=True)
    if not mime.startswith('image/'):
        mylogger.debug(f'image mime type expected, found {mime!r} for submission {submission.id!r}, skipping...')
        return None

    mylogger.debug(f'Getting text via OCR for image at {filepath!r} for submission {submission.id!r}...')
    ocr_string = pytesseract.image_to_string(filepath)
    if not ocr_string.strip():
        mylogger.debug(f'OCR string blank for {submission.id!r}, skipping...')
        return None

    mylogger.debug(
        f'Found text! Putting it through get_string_to_search preprocessor for submission {submission.id!r}...')
    string_to_search = get_string_to_search(ocr_string)
    if not string_to_search:
        mylogger.debug(f'Could not find string to search for {submission.id!r}, skipping...')
        return None

    if len(string_to_search) < 12:
        mylogger.debug(f'String to search too small, skipping: {string_to_search!r}')
        return None

    mylogger.debug(f'String preprocessed! Searching for {string_to_search!r} on Google...')

    prediction = Prediction(link=None, ocr_text=ocr_string, query_text=string_to_search)

    results = search(string_to_search)
    if len(results) == 0:
        mylogger.debug(f'No results found for {string_to_search!r} on Google skipping...')
        return prediction

    prediction.link = results[0]
    mylogger.debug(f'Link {prediction.link!r} found for {string_to_search!r}! Returning...')
    return prediction


def get_reddit() -> Reddit:
    mylogger.debug(f'Attempting to login as {USERNAME!r} with praw...')
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        password=PASSWORD,
        user_agent=f'PornHub Comments Sauce Bot by /u/{USERNAME}',
        username=USERNAME,
    )
    mylogger.debug(f'Logged in as {USERNAME!r} successfully!')
    return reddit


def process_submissions():
    reddit = get_reddit()

    mylogger.debug(f'Getting subreddit {SUBREDDIT!r}...')
    subreddit = reddit.subreddit(SUBREDDIT)
    mylogger.debug(f'Successfully got {SUBREDDIT!r}!')

    mylogger.debug(f'Streaming submissions for {SUBREDDIT!r}...')
    submission: Submission
    for submission in subreddit.stream.submissions():
        mylogger.debug(f'Processing submission ID {submission.id!r}...')
        mylogger.debug(f'''Checking if we've already replied attempted submission {submission.id!r}''')
        replied_submission: Optional[RepliedSubmission] = RepliedSubmission.get_or_none(
            RepliedSubmission.submission_id == submission.id)
        if replied_submission:
            mylogger.debug(f'Entry found in replied_submission, skipping submission {submission.id!r}')
            continue

        if submission.is_self or not submission.url:
            mylogger.debug(f'Submission is self post/URL not found, skipping submission {submission.id!r}')
            RepliedSubmission.create(submission_id=submission.id)
            continue

        mylogger.debug(f'Entry not found in replied_submission, getting prediction for {submission.id!r}...')
        prediction = get_prediction(submission)
        if not (prediction and prediction.link):
            mylogger.debug(f'Prediction could not be computed, skipping submission {submission.id!r}')
            RepliedSubmission.create(
                submission_id=submission.id,
                image_url=submission.url,
                ocr_text=(prediction and prediction.ocr_text),
                query_text=(prediction and prediction.query_text))
            continue

        mylogger.debug(f'Prediction link {prediction.link!r} found for submission {submission.id!r}, getting title...')
        title = get_ph_title(prediction.link)
        if not title:
            mylogger.debug(f'Could not find title, skipping submission {submission.id!r}')
            RepliedSubmission.create(
                submission_id=submission.id,
                image_url=submission.url,
                ocr_text=prediction.ocr_text,
                query_text=prediction.query_text,
                predicted_link=prediction.link)
            continue

        mylogger.debug(f'Title {title!r} found for submission {submission.id!r}, getting replied comment...')
        replied_comment = reply_with_sauce(submission, prediction.link, title)
        if not replied_comment:
            mylogger.debug(f'replied_comment {replied_comment.id!r}, skipping {submission.id!r}')
            RepliedSubmission.create(
                submission_id=submission.id,
                image_url=submission.url,
                ocr_text=prediction.ocr_text,
                query_text=prediction.query_text,
                predicted_link=prediction.link)
            continue

        mylogger.debug(f'Creating new replied submission entry for {submission.id!r}...')
        new_replied_submission = RepliedSubmission.create(
            submission_id=submission.id,
            image_url=submission.url,
            ocr_text=prediction.ocr_text,
            query_text=prediction.query_text,
            predicted_link=prediction.link)
        mylogger.debug(
            f'New replied submission entry {new_replied_submission.id!r} created successfully for {submission.id!r}!')


def process_mentions():
    reddit = get_reddit()

    while True:
        mylogger.debug(f'Iterating over mentions for {USERNAME!r}...')
        comment: Comment
        for comment in reddit.inbox.mentions():
            mylogger.debug(f'Processing mention comment {comment.id!r}...')
            if not (comment.author and comment.author.name and (not DEBUG_MODE or comment.author.name == MAINTAINER)):
                mylogger.warning(f'Author not found for mention comment {comment.id!r}, skipping...')
                continue

            mylogger.debug(f'Checking replied_comment if existing mention comment {comment.id!r} already replied to...')
            replied_comment = RepliedComment.get_or_none(RepliedComment.comment_id == comment.id)
            if replied_comment:
                mylogger.debug(
                    f'Already found replied comment {replied_comment!r} for mention comment {comment.id!r}, skipping...')
                continue

            submission: Submission = comment.submission
            if submission.is_self or not submission.url:
                mylogger.debug(
                    f"Skipping submission {submission.id} without comment because it's a self post/no URL found")
                continue

            mylogger.debug(f'Checking if we already have the predicted link for submission '
                           f'{submission.id!r} of comment {comment.id!r}...')
            replied_submission = RepliedSubmission.get_or_none(RepliedSubmission.submission_id == submission.id)
            if replied_submission and replied_submission.predicted_link:
                predicted_link = replied_submission.predicted_link
                mylogger.debug(f'Predicted link {replied_submission.predicted_link!r} found '
                               f'for {submission.id!r}, no need to lookup again.')

                sauce_comment = None
                _comment: Comment
                for _comment in submission.comments.list():
                    if (isinstance(_comment, Comment) and _comment.author and _comment.author.name == USERNAME
                            and 'Sauce' in _comment.body):
                        sauce_comment = _comment
                        break

                if sauce_comment:
                    mylogger.debug(f'Found sauce comment {sauce_comment.id}, redirecting to it...')
                    comment.reply(f"[I've already provided sauce in this thread here!]"
                                  f"(https://reddit.com/comments/{submission.id}/_/{sauce_comment.id})")
                else:
                    title = get_ph_title(predicted_link)
                    mylogger.debug(f'Title {title!r} found, replying with sauce')
                    prediction = Prediction.from_replied_submission(replied_submission)
                    sauce_comment = reply_with_sauce(comment, prediction.link, title)

                RepliedComment.create(comment_id=comment.id, replied_submission=replied_submission)
                mylogger.debug(f'Replied with sauce to {comment.id!r}. Sauce comment is {sauce_comment.id!r}')
            else:
                mylogger.debug(
                    f'Could not find predicted link in database, getting prediction for {submission.id!r}...')
                prediction = get_prediction(submission)

                sauce_not_found_message = SAUCE_NOT_FOUND_MESSAGE
                if submission.subreddit.display_name != SUBREDDIT:
                    sauce_not_found_message = f'{OTHER_SUB_DISCLAIMER}\n\n{SAUCE_NOT_FOUND_MESSAGE}'

                if not (prediction and prediction.link):
                    RepliedComment.create(comment_id=comment.id)
                    mylogger.debug(f'Failed to get prediction! Issuing apology comment to {comment.id!r}...')
                    apology_comment = comment.reply(sauce_not_found_message)
                    mylogger.debug(f'Apology comment id: {apology_comment.id!r}')
                    continue

                mylogger.debug(f'Got predicted link {prediction.link}, getting title for it...')
                title = get_ph_title(prediction.link)
                if not title:
                    RepliedComment.create(comment_id=comment.id)
                    mylogger.debug(f'Failed to get title! Issuing apology comment to {comment.id!r}...')
                    apology_comment = comment.reply(sauce_not_found_message)
                    mylogger.debug(f'Apology comment id: {apology_comment.id!r}')
                    continue

                mylogger.debug(f'Title {title!r} found, replying with sauce')
                sauce_comment = reply_with_sauce(comment, prediction.link, title)
                if sauce_comment:
                    mylogger.debug(f'Sauce comment: {sauce_comment.id!r} found, saving to replied_submission in DB')
                    replied_submission = RepliedSubmission.create(
                        submission_id=submission.id,
                        image_url=submission.url,
                        ocr_text=prediction.ocr_text,
                        query_text=prediction.query_text,
                        predicted_link=prediction.link)
                    RepliedComment.create(comment_id=comment.id, replied_submission=replied_submission)
                    mylogger.debug(f'Saved to replied_submission: {replied_submission.id!r}')

        time.sleep(60)


if __name__ == '__main__':
    import sys

    first_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if first_arg == 'submissions':
        process_submissions()
    elif first_arg == 'mentions':
        process_mentions()
    else:
        mylogger.error(f'Usage: {sys.argv[0]} [submissions|mentions]')
        sys.exit(1)
