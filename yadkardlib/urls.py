#!/data/project/yadkard/venv/bin/python
# -*- coding: utf-8 -*-

'''Codes used for parsing contents of an arbitrary URL.'''

import re
from datetime import datetime
from urlparse import urlparse
import warnings

import requests
from bs4 import BeautifulSoup as BS
import langid


import conv
import config

if config.lang == 'en':
    import wikiref_en as wikiref
    import wikicite_en as wikicite
else:
    import wikiref_fa as wikiref
    import wikicite_fa  as wikicite


class Citation():

    '''Create citation object.'''

    def __init__(self, url):
        self.url = url
        self.dictionary = url2dictionary(url)
        self.ref = wikiref.create(self.dictionary)
        self.cite = wikicite.create(self.dictionary)
        self.error = 0


class StatusCodeError(Exception):

    '''Raise when requests.get.status_code != 200.'''

    pass


def find_sitename(bs):
    '''Return site's name as a string.

Get a BeautifulSoup object of a webpage. Return site's name as a string.
'''
    try:
        return bs.find(attrs={'name':'og:site_name'})['content'].strip()
    except Exception:
        pass
    try:
        #https://www.bbc.com/news/science-environment-26878529
        return bs.find(attrs={'property':'og:site_name'})['content'].strip()
    except Exception:
        pass
    try:
        #http://www.nytimes.com/2007/06/13/world/americas/13iht-whale.1.6123654.html?_r=0
        return bs.find(attrs={'name':'PublisherName'})['value'].strip()
    except Exception:
        pass
    try:
        #http://www.bbc.com/news/science-environment-26878529 (Optional)
        return bs.find(attrs={'name':'CPS_SITE_NAME'})['content'].strip()
    except Exception:
        pass
    try:
        #http://www.nytimes.com/2013/10/01/science/a-wealth-of-data-in-whale-breath.html
        return bs.find(attrs={'name':'cre'})['content'].strip()
    except Exception:
        pass


def find_title(bs):
    '''Get a BeautifulSoup object and return title as a string.'''
    try:
        #http://www.telegraph.co.uk/earth/earthnews/6190335/Whale-found-dead-in-Thames.html
        #Should be tried before og:title
        return bs.find(attrs={'name':'title'})['content'].strip()
    except Exception:
        pass
    try:
        #http://www.bostonglobe.com/ideas/2014/04/28/new-study-reveals-how-honky-tonk-hits-respond-changing-american-fortunes/9ep0iPknDBl9EFFaoXfbmL/comments.html
        #Should be tried before og:title
        return bs.find(class_='main-hed').text.strip()
    except Exception:
        pass
    try:
        #http://www.bbc.com/news/science-environment-26878529
        return bs.find(attrs={'property':'og:title'})['content'].strip()
    except Exception:
        pass
    try:
        #http://www.bbc.com/news/science-environment-26267918
        return bs.find(attrs={'name':'Headline'})['content'].strip()
    except Exception:
        pass
    try:
        #http://www.nytimes.com/2007/06/13/world/americas/13iht-whale.1.6123654.html?_r=0
        return bs.find(class_='articleHeadline').text.strip()
    except Exception:
        pass
    try:
        #http://www.nytimes.com/2007/09/11/us/11whale.html
        return bs.find(attrs={'name':'hdl'})['content'].strip()
    except Exception:
        pass
    try:
        return bs.h1.text.strip()
    except Exception:
        pass
    try:
        return bs.title.text.strip()
    except Exception:
        pass


def find_date(bs):
    '''Get a BeautifulSoup object and find the date in it.

Return result as a datetime object.
'''
    try:
        #http://www.telegraph.co.uk/news/worldnews/northamerica/usa/9872625/Kasatka-the-killer-whale-gives-birth-in-pool-at-Sea-World-in-San-Diego.html
        m = bs.find(attrs={'name':'last-modified'})
        return conv.finddate(m['content']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        #http://www.mirror.co.uk/news/weird-news/amazing-rescue-drowning-diver-saved-409479
        #should be placed before article:modified_time
        m = bs.find(attrs={'itemprop':'datePublished'})
        return conv.finddate(m['datetime']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        #http://www.mirror.co.uk/news/uk-news/how-reid-will-get-it-all-off-pat--535323
        #should be placed before article:modified_time
        m = bs.find(attrs={'data-type':'pub-date'})
        return conv.finddate(m.text).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        m = bs.find(attrs={'property':'article:modified_time'})
        return conv.finddate(m['content']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        m = bs.find(attrs={'property':'article:published_time'})
        return conv.finddate(m['content']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        m = bs.find(attrs={'name':'OriginalPublicationDate'})
        return conv.finddate(m['content']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        m = bs.find(attrs={'name':'publish-date'})
        return conv.finddate(m['content']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        m = bs.find(attrs={'name':'pub_date'})
        return conv.finddate(m['content']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        #http://www.nytimes.com/2007/06/13/world/americas/13iht-whale.1.6123654.html?_r=0
        m = bs.find(class_='dateline').text
        return conv.finddate(m).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        #http://www.nytimes.com/2003/12/14/us/willy-whale-dies-in-norway.html
        m = bs.find(attrs={'name':'DISPLAYDATE'})
        return conv.finddate(m['content']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        #http://www.washingtonpost.com/wp-dyn/content/article/2006/01/19/AR2006011902990.html
        m = bs.find(attrs={'name':'DC.date.issued'})
        return conv.finddate(m['content']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        m = bs.find(attrs={'name':'sailthru.date'})
        #http://www.huffingtonpost.ca/arti-patel/nina-davuluri_b_3936174.html
        return conv.finddate(m['content']).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        m = unicode(bs.find(class_='updated'))
        return conv.finddate(m).strftime('%Y-%m-%d')
    except Exception:
        pass
    #https://www.bbc.com/news/uk-england-25462900
    try:
        warnings.warn('Finding date in bs.text.')
        return conv.finddate(bs.text).strftime('%Y-%m-%d')
    except Exception:
        pass


def find_byline_names(bs):
    '''Get a BeautifulSoup object and return byline names as list.'''
    try:
        #http://www.telegraph.co.uk/science/science-news/3313298/Marine-collapse-linked-to-whale-decline.html
        m = bs.find(attrs={'name':'author'})
        return byline_to_names(m['content'])
    except Exception:
        pass
    try:
        #http://www.telegraph.co.uk/science/8323909/The-sperm-whale-works-in-extraordinary-ways.html
        m = bs.find(attrs={'name':'DCSext.author'})
        return byline_to_names(m['content'])
    except Exception:
        pass
    try:
        #http://news.bbc.co.uk/2/hi/business/2570109.stm
        m = bs.find(class_='bylineAuthor').text
        return byline_to_names(m)
    except Exception:
        pass
    try:
        #http://www.bbc.com/news/science-environment-26267918
        m = bs.find(class_='byline-name').text
        return byline_to_names(m)
    except Exception:
        pass
    try:
        m = bs.find(class_='story-byline').text
        return byline_to_names(m)
    except Exception:
        pass
    try:
        #http://www.dailymail.co.uk/news/article-2633025/
        names = []
        for m in bs.find_all(class_='author'):
            names.extend(byline_to_names(m.text))
        if not names:
            raise Exception('"names" remained an empty list.')
        return names
    except Exception:
        pass
    try:
        m = bs.find(class_='byline').text
        return byline_to_names(m)
    except Exception:
        pass
    try:
        #http://www.washingtonpost.com/wp-dyn/content/article/2006/12/20/AR2006122002165.html
        m = bs.find(id='byline').text
        return byline_to_names(m)
    except Exception:
        pass
    try:
        #http://news.bbc.co.uk/2/hi/programmes/newsnight/5178122.stm
        m = bs.find(class_='byl').text
        return byline_to_names(m)
    except Exception:
        pass
    try:
        #http://www.nytimes.com/2003/10/09/us/adding-weight-to-suspicion-sonar-is-linked-to-whale-deaths.html
        m = bs.find(attrs={'name':'byl'})
        return byline_to_names(m['content'])
    except Exception:
        pass
    try:
        m = bs.find(class_='name').text
        return byline_to_names(m)
    except Exception:
        pass
    try:
        #http://voices.washingtonpost.com/thefix/eye-on-2008/2008-whale-update.html
        m = re.search('[\n>"\']\s*By\s*(.*)[<\n"\']',bs.text).group(1)
        return byline_to_names(m)
    except Exception:
        pass
    

def byline_to_names(byline):
    '''Find authors in byline sting. Return name objects as a list.

The "By " prefix will be omitted.
Names will be seperated either with " and " or ", ".
'''
    if '|' in byline:
        raise Exception('Invalid character ("|") in byline.')
    byline = byline.strip()
    if byline.startswith('By '):
        byline = byline[3:]
    byline = re.split(' and |, ', byline)
    names = []
    for fullname in byline:
        if ' in ' in fullname:
            #http://www.telegraph.co.uk/earth/earthnews/3324585/Shocking-pictures-of-Japanese-whaling.html
            fullname = fullname.split(' in ')[0]
        name = conv.Name(fullname)
        if ('Reporter' in name.lastname) or ('People' in name.lastname):
            name.nofirst_fulllast()
        if 'Editor' in name.lastname:
            #http://www.telegraph.co.uk/education/3296593/Inner-ear-offers-clue-to-when-whales-first-swam.html
            #http://www.telegraph.co.uk/news/worldnews/1335525/Plan-to-cut-whaling-dropped.html
            continue
        names.append(name)
    return names


def url2dictionary(url):
    '''Get url and return the result as a dictionary.'''
    r = requests.get(url)
    if r.status_code != 200:
        raise StatusCodeError, r.status_code
    d = {}
    d['url'] = url
    d['type'] = 'web'
    bs = BS(r.text)
    d['website'] = find_sitename(bs)
    if not d['website']:
        if urlparse(url)[1].startswith('www.'):
            d['website'] = urlparse(url)[1][4:]
        else:
            d['website'] = urlparse(url)[1]
    m = find_title(bs)
    if m:
        d['title'] = m
    m = find_date(bs)
    if m:
        d['date'] = m
        d['year'] = d['date'][:4]
    d['authors'] = find_byline_names(bs)
    if not d['authors']:
        del d['authors']
    return d
