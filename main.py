# [START app]
import os
import logging
import random
import tweepy

from flask import Flask, render_template, request
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types

app = Flask(__name__)


def collect_tweets(target):
    auth = tweepy.AppAuthHandler(os.environ['TWITTER_CONSUMER_KEY'], os.environ['TWITTER_CONSUMER_SECRET'])
    api = tweepy.API(auth)
    try:
        tweets = []
        for status in api.user_timeline(target, include_rts=False, count=100, exclude_replies=True):
            tweets.append(status.text)
        return '\n'.join(tweets)
    except tweepy.error.TweepError:
        return ''


def process(text):
    # Instantiates a client
    client = language.LanguageServiceClient()
    # Instantiates a plain text document.
    document = types.Document(
        content=text,
        type=enums.Document.Type.PLAIN_TEXT)
    # Detects the sentiment of the text
    result_analyze_sentiment = client.analyze_sentiment(document=document)
    # Calculate total score
    total_score = 0.0
    for sentence in result_analyze_sentiment.sentences:
        total_score += sentence.sentiment.magnitude * sentence.sentiment.score
    # Detects entities in the document.
    result_analyze_entities = client.analyze_entities(document=document)
    # 
    entities = set()
    for entity in result_analyze_entities.entities:
        if entity.type not in ['OTHER', 'UNKNOWN']:
            entities.add(entity.name)
    return total_score, entities


@app.route('/analyze', methods=['POST'])
def analyze():
    screen_name = request.form['screen_name']
    text = collect_tweets(screen_name)
    if text == '':
        return render_template('error.html')

    total_score, entities = process(text)
    comment = 'ポジティブ！' if total_score > 0.0 else 'ネガティブ！'
    if abs(total_score) > 10.0:
        comment = 'とっても' + comment
    elif abs(total_score) > 5.0:
        comment = 'かなり' + comment
    else:
        comment = 'どちらかというと' + comment
    samples = random.sample(entities, min(7, len(entities)))
    return render_template('result.html',
                           screen_name=screen_name,
                           total_score=total_score,
                           comment=comment,
                           samples=samples)


@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500

if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
# [END app]
