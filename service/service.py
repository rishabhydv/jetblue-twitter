import os
import sys
import logging
import requests
import traceback
from flask import Flask, jsonify, request, url_for, make_response, abort, json
from flask_api import status    # HTTP Status Codes
from werkzeug.exceptions import NotFound
import tweepy
import re

from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
from datetime import datetime, timedelta
from nltk.tokenize import WordPunctTokenizer

# Import Flask application
from . import app
######################################################################
# LIST ALL ITEMS IN ONE SHOP CART ---
######################################################################
ACC_TOKEN = '2248351440-2ZV6lx2GkHBjKnyG1rdwhImPW3RdHztaYsEoT8I'
ACC_SECRET = 'p5Podwa6oxGv3R7A0dhX4wB8OPkAQp7PMKkhJG9IYMbO5'
CONS_KEY = '5nm5Z7Ms5WbyybdBR4UH07Q5t'
CONS_SECRET = 'KAAlEhltHgntE1IHFDpdqTF09q7GHEDhhhsAZQ3nfPesa4giNT'
SEARCH_PARAM = 'JetBlue'
TOTAL_TWEETS = 10

@app.route('/jetblue', methods=['GET'])
def list_tweets():
    """ Returns list of all tweets with keyword JetBlueSucks"""
    app.logger.info('Request to list all tweets with sentiment score for search param: %s', SEARCH_PARAM)
    results = analyze_tweets(SEARCH_PARAM,TOTAL_TWEETS)
    return make_response(jsonify(results), status.HTTP_200_OK)

def authentication(cons_key, cons_secret, acc_token, acc_secret):
    auth = tweepy.OAuthHandler(cons_key, cons_secret)
    auth.set_access_token(acc_token, acc_secret)
    api = tweepy.API(auth)
    return api
    
def search_tweets(keyword, total_tweets):
    today_datetime = datetime.today().now()
    yesterday_datetime = today_datetime - timedelta(days=7)
    today_date = today_datetime.strftime('%Y-%m-%d')
    yesterday_date = yesterday_datetime.strftime('%Y-%m-%d')
    api = authentication(CONS_KEY,CONS_SECRET,ACC_TOKEN,ACC_SECRET)
    search_result = tweepy.Cursor(api.search, 
                                  q=keyword, 
                                  since=yesterday_date, 
                                  result_type='recent', 
                                  lang='en').items(total_tweets)
    return search_result

def clean_tweets(tweet):
    user_removed = re.sub(r'@[A-Za-z0-9]+','',tweet.decode('utf-8'))
    link_removed = re.sub('https?://[A-Za-z0-9./]+','',user_removed)
    number_removed = re.sub('[^a-zA-Z]', ' ', link_removed)
    lower_case_tweet= number_removed.lower()
    tok = WordPunctTokenizer()
    words = tok.tokenize(lower_case_tweet)
    clean_tweet = (' '.join(words)).strip()
    return clean_tweet

def get_sentiment_score(tweet):
    client = language.LanguageServiceClient()
    document = types\
               .Document(content=tweet,
                         type=enums.Document.Type.PLAIN_TEXT)
    sentiment_score = client\
                      .analyze_sentiment(document=document)\
                      .document_sentiment\
                      .score
    return sentiment_score

def analyze_tweets(keyword, total_tweets):
    score = 0
    result_dict = {}
    twitter_score_list=[]
    try:
        tweets = search_tweets(keyword,total_tweets)
        print(tweets)
        for tweet in tweets:
            print("1")
            twitter_score_dict = {}
            cleaned_tweet = clean_tweets(tweet.text.encode('utf-8'))
            sentiment_score = get_sentiment_score(cleaned_tweet)
            score += sentiment_score
            #print(cleaned_tweet)
            twitter_score_dict['tweet'] = cleaned_tweet
            twitter_score_dict['score'] = sentiment_score
            twitter_score_list.append(twitter_score_dict)
        final_score = round((score / float(total_tweets)),2)
        result_dict['finalScore'] = final_score
        result_dict['data'] = twitter_score_list
    except Exception as e:
        app.logger.error("Unable to get data for tweets")
        app.logger.error(e)
        traceback.print_exc()
        result_dict['finalScore'] = 0
        result_dict['data'] = []
    
    return result_dict
######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################

def check_content_type(content_type):
    """ Checks that the media type is correct """
    if request.headers['Content-Type'] == content_type:
        return
    app.logger.error('Invalid Content-Type: %s', request.headers['Content-Type'])
    abort(415, 'Content-Type must be {}'.format(content_type))

def initialize_logging(log_level=logging.INFO):
    """ Initialized the default logging to STDOUT """
    if not app.debug:
        print('Setting up logging...')
        # Set up default logging for submodules to use STDOUT
        # datefmt='%m/%d/%Y %I:%M:%S %p'
        fmt = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        logging.basicConfig(stream=sys.stdout, level=log_level, format=fmt)
        # Make a new log handler that uses STDOUT
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt))
        handler.setLevel(log_level)
        # Remove the Flask default handlers and use our own
        handler_list = list(app.logger.handlers)
        for log_handler in handler_list:
            app.logger.removeHandler(log_handler)
        app.logger.addHandler(handler)
        app.logger.setLevel(log_level)
        app.logger.propagate = False
        app.logger.info('Logging handler established')
