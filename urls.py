#! /usr/bin/python
# -*- coding: utf-8 -*-

"""Codes used for parsing contents of an arbitrary URL."""


import re
from urllib.parse import urlparse
import logging
from difflib import get_close_matches
from threading import Thread

from requests import get as requests_get
from requests import get as requests_head

from requests.exceptions import RequestException
from bs4 import SoupStrainer, BeautifulSoup

from commons import (
    finddate, detect_language, BaseResponse, USER_AGENT_HEADER,
    dictionary_to_citations,
)
from urls_authors import find_authors


TITLE_FIND_PARAMETERS = (
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    ({'name': 'citation_title'}, 'getitem', 'content'),
    # http://www.telegraph.co.uk/earth/earthnews/6190335/Whale-found-dead-in-Thames.html
    # Should be tried before og:title
    ({'name': 'title'}, 'getitem', 'content'),
    # http://www.bostonglobe.com/ideas/2014/04/28/new-study-reveals-how-honky-tonk-hits-respond-changing-american-fortunes/9ep0iPknDBl9EFFaoXfbmL/comments.html
    # Should be tried before og:title
    ({'class': 'main-hed'}, 'getattr', 'text'),
    # http://timesofindia.indiatimes.com/city/thiruvananthapuram/Whale-shark-dies-in-aquarium/articleshow/32607977.cms
    # Should be tried before og:title
    ({'class': 'arttle'}, 'getattr', 'text'),
    # http://www.bbc.com/news/science-environment-26878529
    ({'property': 'og:title'}, 'getitem', 'content'),
    # http://www.bbc.com/news/science-environment-26267918
    ({'name': 'Headline'}, 'getitem', 'content'),
    # http://www.nytimes.com/2007/06/13/world/americas/13iht-whale.1.6123654.html?_r=0
    ({'class': 'articleHeadline'}, 'getattr', 'text'),
    # http://www.nytimes.com/2007/09/11/us/11whale.html
    ({'name': 'hdl'}, 'getitem', 'content'),
    # http://ftalphaville.ft.com/2012/05/16/1002861/recap-and-tranche-primer/?Authorised=false
    ({'class': 'entry-title'}, 'getattr', 'text'),
    # http://voices.washingtonpost.com/thefix/eye-on-2008/2008-whale-update.html
    ({'id': 'entryhead'}, 'getattr', 'text'),
)


DATE_FIND_PARAMETERS = (
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    ({'name': 'citation_date'}, 'getitem', 'content'),
    # http://jn.physiology.org/content/81/1/319
    ({'name': 'citation_publication_date'}, 'getitem', 'content'),
    # http://www.telegraph.co.uk/news/worldnews/northamerica/usa/9872625/Kasatka-the-killer-whale-gives-birth-in-pool-at-Sea-World-in-San-Diego.html
    ({'name': 'last-modified'}, 'getitem', 'content'),
    # http://www.mirror.co.uk/news/weird-news/amazing-rescue-drowning-diver-saved-409479
    # should be placed before article:modified_time
    ({'itemprop': 'datePublished'}, 'getitem', 'datetime'),
    # http://www.mirror.co.uk/news/uk-news/how-reid-will-get-it-all-off-pat--535323
    # should be placed before article:modified_time
    ({'data-type': 'pub-date'}, 'getattr', 'text'),
    # http://dealbook.nytimes.com/2014/05/30/insider-trading-inquiry-includes-mickelson-and-icahn/
    # place before {'property': 'article:modified_time'}
    ({'property': 'article:published_time'}, 'getitem', 'content'),
    # http://www.dailymail.co.uk/news/article-2384832/Great-White-sharks-hunt-seals-South-Africa.html
    ({'property': 'article:modified_time'}, 'getitem', 'content'),
    # http://www.tgdaily.com/web/100381-apple-might-buy-beats-for-32-billion
    ({'property': 'dc:date dc:created'}, 'getitem', 'content'),
    # http://www.bbc.co.uk/news/science-environment-20890389
    ({'name': 'OriginalPublicationDate'}, 'getitem', 'content'),
    ({'name': 'publish-date'}, 'getitem', 'content'),
    # http://www.washingtonpost.com/wp-srv/style/movies/reviews/godsandmonsterskempley.htm
    ({'name': 'pub_date'}, 'getitem', 'content'),
    # http://www.economist.com/node/1271090?zid=313&ah=fe2aac0b11adef572d67aed9273b6e55
    ({'name': 'pubdate'}, 'getitem', 'content'),
    # http://www.ft.com/cms/s/ea29ffb6-c759-11e0-9cac-00144feabdc0,Authorised=false.html?_i_location=http%3A%2F%2Fwww.ft.com%2Fcms%2Fs%2F0%2Fea29ffb6-c759-11e0-9cac-00144feabdc0.html%3Fsiteedition%3Duk&siteedition=uk&_i_referer=#axzz31G5ZgwCH
    ({'id': 'publicationDate'}, 'getattr', 'text'),
    # http://www.nytimes.com/2007/06/13/world/americas/13iht-whale.1.6123654.html?_r=0
    ({'class': 'dateline'}, 'getattr', 'text'),
    # http://www.nytimes.com/2003/12/14/us/willy-whale-dies-in-norway.html
    ({'name': 'DISPLAYDATE'}, 'getitem', 'content'),
    # http://www.washingtonpost.com/wp-dyn/content/article/2006/01/19/AR2006011902990.html
    ({'name': 'DC.date.issued'}, 'getitem', 'content'),
    # http://www.farsnews.com/newstext.php?nn=13930418000036
    ({'name': 'dc.Date'}, 'getitem', 'content'),
    # http://www.huffingtonpost.ca/arti-patel/nina-davuluri_b_3936174.html
    ({'name': 'sailthru.date'}, 'getitem', 'content'),
    # http://ftalphaville.ft.com/2012/05/16/1002861/recap-and-tranche-primer/?Authorised=false
    ({'class': 'entry-date'}, 'getattr', 'text'),
    # http://www.huffingtonpost.com/huff-wires/20121203/us-sci-nasa-voyager/
    ({'class': 'updated'}, 'getattr', 'text'),
    # http://timesofindia.indiatimes.com/city/thiruvananthapuram/Whale-shark-dies-in-aquarium/articleshow/32607977.cms
    ({'class': 'byline'}, 'getattr', 'text'),
    # http://www.highbeam.com/doc/1P3-3372742961.html
    ({'id': 'docByLine'}, 'getattr', 'text'),
    # wikipedia
    ({'id': 'footer-info-lastmod'}, 'getattr', 'text'),
)


class UrlsResponse(BaseResponse):

    """Create URL's response object."""

    def __init__(self, url: str, date_format: str='%Y-%m-%d') -> None:
        """Make the dictionary and run self.generate()."""
        try:
            dictionary = url2dictionary(url)
            dictionary['date_format'] = date_format
            self.cite, self.sfn, self.ref = dictionary_to_citations(dictionary)
        except (ContentTypeError, ContentLengthError) as e:
            self.sfnt = 'Could not process the request.'
            self.ctnt = e
            self.error = 100
            logger.exception(url)


class ContentTypeError(ValueError):

    """Raise when content-type header does not start with 'text/'."""

    pass


class ContentLengthError(ValueError):

    """Raise when content-length header indicates a very long content."""

    pass


class StatusCodeError(ValueError):

    """Raise when requests_get.status_code != 200."""

    pass


def find_journal(soup: BeautifulSoup) -> str:
    """Return journal title as a string."""
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    m = soup.find(attrs={'name': 'citation_journal_title'})
    if m:
        return m['content'].strip()


def find_url(soup: BeautifulSoup, url: str) -> str:
    """Return og:url or url as a string."""
    # http://www.ft.com/cms/s/836f1b0e-f07c-11e3-b112-00144feabdc0,Authorised=false.html?_i_location=http%3A%2F%2Fwww.ft.com%2Fcms%2Fs%2F0%2F836f1b0e-f07c-11e3-b112-00144feabdc0.html%3Fsiteedition%3Duk&siteedition=uk&_i_referer=http%3A%2F%2Fwww.ft.com%2Fhome%2Fuk
    f = soup.find(attrs={'property': 'og:url'})
    if f:
        ogurl = f['content']
        if urlparse(ogurl).path:
            return ogurl
    return url


def find_issn(soup: BeautifulSoup) -> str:
    """Return International Standard Serial Number as a string.

    Normally ISSN should be in the  '\d{4}\-\d{3}[\dX]' format, but this
    function does not check that.
    """
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    # http://psycnet.apa.org/journals/edu/30/9/641/
    f = soup.find(attrs={'name': 'citation_issn'})
    if f:
        return f['content'].strip()


def find_pmid(soup: BeautifulSoup) -> str:
    """Return pmid as a string."""
    # http://jn.physiology.org/content/81/1/319
    m = soup.find(attrs={'name': 'citation_pmid'})
    if m:
        return m['content']


def find_doi(soup: BeautifulSoup) -> str:
    """Get the BeautifulSoup object of a page. Return DOI as a string."""
    # http://jn.physiology.org/content/81/1/319
    m = soup.find(attrs={'name': 'citation_doi'})
    if m:
        return m['content']


def find_volume(soup: BeautifulSoup) -> str:
    """Return citatoin volume number as a string."""
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    m = soup.find(attrs={'name': 'citation_volume'})
    if m:
        return m['content'].strip()


def find_issue(soup: BeautifulSoup) -> str:
    """Return citatoin issue number as a string."""
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    m = soup.find(attrs={'name': 'citation_issue'})
    if m:
        return m['content'].strip()


def find_pages(soup: BeautifulSoup) -> str:
    """Return citation pages as a string."""
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    fp = soup.find(attrs={'name': 'citation_firstpage'})
    lp = soup.find(attrs={'name': 'citation_lastpage'})
    if fp and lp:
        return fp['content'].strip() + '–' + lp['content'].strip()


def find_sitename(
    soup: BeautifulSoup,
    url: str,
    authors: list,
    hometitle: list,
    thread: Thread,
) -> tuple:
    """Return (site's name as a string, where).

    Parameters:
        soup: BeautifulSoup object of the page being processed.
        url: URL of the page.
        authors: Authors list returned from find_authors function.
        hometitle: A list containing hometitle string.
        thread: The thread that should be joined before using hometitle_list.
    Returns site's name as a string.
    """
    attrs = {'name': 'og:site_name'}
    f = soup.find(attrs=attrs)
    if f:
        return f.get('content').strip(), attrs
    # https://www.bbc.com/news/science-environment-26878529
    attrs = {'property': 'og:site_name'}
    f = soup.find(attrs=attrs)
    if f:
        return f['content'].strip(), attrs
    # http://www.nytimes.com/2007/06/13/world/americas/13iht-whale.1.6123654.html?_r=0
    attrs = {'name': 'PublisherName'}
    f = soup.find(attrs=attrs)
    if f:
        return f['value'].strip(), attrs
    # http://www.bbc.com/news/science-environment-26878529 (Optional)
    attrs = {'name': 'CPS_SITE_NAME'}
    f = soup.find(attrs=attrs)
    if f:
        return f['content'].strip(), attrs
    # http://www.nytimes.com/2013/10/01/science/a-wealth-of-data-in-whale-breath.html
    attrs = {'name': 'cre'}
    f = soup.find(attrs=attrs)
    if f:
        return f['content'].strip(), attrs
    # search the title
    sitename = parse_title(
        soup.title.text, url, authors, hometitle, thread
    )[2]
    if sitename:
        return sitename, 'parse_title'
    try:
        # using hometitle
        thread.join()
        if ':' in hometitle[0]:
            # http://www.washingtonpost.com/wp-dyn/content/article/2005/09/02/AR2005090200822.html
            sitename = hometitle[0].split(':')[0].strip()
            if sitename:
                return sitename, 'hometitle.split(":")[0]'
        sitename = parse_title(hometitle[0], url, None)[2]
        if sitename:
            return sitename, 'parsed hometitle'
        return hometitle[0], 'hometitle[0]'
    except Exception:
        pass
    # return hostname
    if urlparse(url).hostname.startswith('www.'):
        return urlparse(url).hostname[4:], 'hostname'
    else:
        return urlparse(url).hostname, 'hostname'


def try_find(soup: BeautifulSoup, find_parameters: tuple) -> tuple:
    """Return the first matching item in find_paras as (string, used_attrs).

    args:
        soup: The beautiful soup object.
        find_parameters: List of parameters to try on soup in the following
            format:
                ({atrr_name, value}, 'getitem|getattr', 'content|text|...')
                where {atrrn, value} will be used in
                bs.find(attrs={atrrn, value}).
    Return (None, None) if none of the parameters match bs.
    """
    for attrs, get, value in find_parameters:
        m = soup.find(attrs=attrs)
        if not m:
            continue
        if get == 'getitem':
            result = m.get(value, None)
        else:
            #  get == 'getattr'
            result = getattr(m, value, None)
        if result:
            return result.strip(), attrs
    return None, None


def find_title(
    soup: BeautifulSoup,
    url: str,
    authors: list,
    hometitle: list,
    thread: Thread,
) -> tuple:
    """Return (title_string, where_info)."""
    raw_title, tag = try_find(soup, TITLE_FIND_PARAMETERS)
    if not raw_title:
        try:
            raw_title, tag = soup.title.text.strip(), 'soup.title.text'
        except Exception:
            pass
    if raw_title:
        logger.debug('Unparsed title tag: ' + str(tag))
        parsed_title = parse_title(raw_title, url, authors, hometitle,
                                   thread)
        logger.debug('Parsed title: ' + str(parsed_title))
        return parsed_title[1], tag
    else:
        return None, None


def parse_title(
    title: str,
    url: str,
    authors: list or None,
    hometitle_list=None,
    thread=None,
) -> tuple:
    """Return (intitle_author, pure_title, intitle_sitename).

    Examples:

    >>> parse_title("Rockhopper raises Falklands oil estimate - FT.com",
            "http://www.ft.com/cms/s/ea29ffb6-c759-11e0-9cac-00144feabdc0",
            None)
    (None, 'Rockhopper raises Falklands oil estimate', 'FT.com')

    >>> parse_title('some title - FT.com - something unknown',
            "http://www.ft.com/cms/s/ea29ffb6-c759-11e0-9cac-00144feabdc0",
            None)
    (None, 'some title - something unknown', 'FT.com')

    >>> parse_title("Alpha decay - Wikipedia, the free encyclopedia",
            "https://en.wikipedia.org/wiki/Alpha_decay",
            None)
    (None, 'Alpha decay', 'Wikipedia, the free encyclopedia')

    >>> parse_title("	BBC NEWS | Health | New teeth 'could soon be grown'",
            'http://news.bbc.co.uk/2/hi/health/3679313.stm',
            None)
    (None, "Health - New teeth 'could soon be grown'", 'BBC NEWS')
    """
    intitle_author = intitle_sitename = None
    sep_regex = ' - | — |\|'
    title_parts = re.split(sep_regex, title.strip())
    if len(title_parts) == 1:
        return None, title, None
    hostname = urlparse(url).hostname.replace('www.', '')
    # Searching for intitle_sitename
    # 1. In hostname
    hnset = set(hostname.split('.'))
    for part in title_parts:
        if (part in hostname) or not set(part.lower().split()) - hnset:
            intitle_sitename = part
            break
    if not intitle_sitename:
        # 2. Using difflib on hostname
        # Cutoff = 0.3: 'BBC - Homepage' will match u'‭BBC ‮فارسی‬'
        close_matches = get_close_matches(
            hostname, title_parts, n=1, cutoff=.3
        )
        if close_matches:
            intitle_sitename = close_matches[0]
    if not intitle_sitename:
        if thread:
            thread.join()
        if hometitle_list:
            hometitle = hometitle_list[0]
        else:
            hometitle = ''
        # 3. In homepage title
        for part in title_parts:
            if part in hometitle:
                intitle_sitename = part
                break
    if not intitle_sitename:
        # 4. Using difflib on hometitle
        close_matches = get_close_matches(
            hometitle, title_parts, n=1, cutoff=.3
        )
        if close_matches:
            intitle_sitename = close_matches[0]
    # Remove sitename from title_parts
    if intitle_sitename:
        title_parts.remove(intitle_sitename)
        intitle_sitename = intitle_sitename.strip()
    # Searching for intitle_author
    if authors:
        for author in authors:
            for part in title_parts:
                if author.lastname.lower() in part.lower():
                    intitle_author = part
                    break
    # Remove intitle_author from title_parts
    if intitle_author:
        title_parts.remove(intitle_author)
        intitle_author = intitle_author.strip()
    pure_title = ' - '.join(title_parts)
    return intitle_author, pure_title, intitle_sitename


def try_find_date(soup: BeautifulSoup) -> tuple:
    """Similar to try_find(), but for finding dates.

    Return a string in '%Y-%m-%d' format.
    """
    for fp in DATE_FIND_PARAMETERS:
        try:
            attrs = fp[0]
            m = soup.find(attrs=attrs)
            if fp[1] == 'getitem':
                string = m[fp[2]]
                date = finddate(string)
                if date:
                    return date, attrs
            elif fp[1] == 'getattr':
                string = getattr(m, fp[2])
                date = finddate(string)
                if date:
                    return date, attrs
        except (TypeError, AttributeError, KeyError):
            pass
    return None, None


def find_date(soup: BeautifulSoup, url: str) -> tuple:
    """Get the BeautifulSoup object and url. Return (date_obj, where)."""
    date, tag = try_find_date(soup)
    if date:
        return date, tag
    else:
        # http://ftalphaville.ft.com/2012/05/16/1002861/recap-and-tranche-primer/?Authorised=false
        date = finddate(url)
    if date:
        return date, 'url'
    else:
        # https://www.bbc.com/news/uk-england-25462900
        date = finddate(soup.text)
    if date:
        return date, 'soup.text'
    else:
        logger.info('Searching for date in page content.\n' + url)
        return finddate(str(soup)), 'str(soup)'


def get_hometitle(url: str, headers: dict, hometitle_list: list) -> None:
    """Get homepage of the url and return it's title.

    hometitle_list will be used to return the thread result.
    This function is invoked through a thread.
    """
    homeurl = '://'.join(urlparse(url)[:2])
    try:
        requests_visa(homeurl, headers)
        content = requests_get(homeurl, headers=headers, timeout=15).content
        strainer = SoupStrainer('title')
        soup = BeautifulSoup(content, 'lxml', parse_only=strainer)
        hometitle_list.append(soup.title.text.strip())
    except RequestException:
        pass


def requests_visa(url: str, request_headers: dict=None) -> bool:
    """Check content-type and content-length of the response.

    Return True if content-type is text/* and content-length is less than 1MB.
    Also return True if no information is available. Else return False.
    """
    response_headers = requests_head(url, headers=request_headers).headers
    if 'content-length' in response_headers:
        megabytes = int(response_headers['content-length']) / 1000000.
        if megabytes > 1:
            raise ContentLengthError(
                'Content-length was too long. (' +
                format(megabytes, '.2f') + ' MB)'
            )
    if 'content-type' in response_headers:
        if response_headers['content-type'].startswith('text/'):
            return True
        else:
            raise ContentTypeError(
                'Invalid content-type: ' +
                response_headers['content-type'] +
                ' (URL-content is supposed to be text/html)'
            )
    return True


def get_soup(url: str, headers: dict=None) -> BeautifulSoup:
    """Return the soup object for the given url."""
    requests_visa(url, headers)
    r = requests_get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise StatusCodeError(r.status_code)
    return BeautifulSoup(r.content, 'lxml')


def url2dictionary(url: str, detect_lang: bool=True) -> dict:
    """Get url and return the result as a dictionary."""
    # Creating a thread to fetch homepage title in background
    hometitle_list = []  # A mutable variable used to get the thread result
    home_title_thread = Thread(
        target=get_hometitle, args=(url, USER_AGENT_HEADER, hometitle_list)
    )
    home_title_thread.start()

    soup = get_soup(url, USER_AGENT_HEADER)
    d = {'url': find_url(soup, url)}
    authors, tag = find_authors(soup)
    if authors:
        logger.debug('Authors tag: ' + str(tag))
        d['authors'] = authors
    d['doi'] = find_doi(soup)
    d['issn'] = find_issn(soup)
    d['pmid'] = find_pmid(soup)
    d['volume'] = find_volume(soup)
    d['issue'] = find_issue(soup)
    d['pages'] = find_pages(soup)
    d['journal'] = find_journal(soup)
    if d['journal']:
        d['type'] = 'jour'
    else:
        d['type'] = 'web'
        d['website'], tag = find_sitename(soup, url, authors, hometitle_list,
                                          home_title_thread)
        logger.debug('Website tag: ' + str(tag))
    d['title'], tag = find_title(
        soup, url, authors, hometitle_list, home_title_thread
    )
    date, tag = find_date(soup, url)
    if date:
        logger.debug('Date tag: ' + str(tag))
        d['date'] = date
        d['year'] = str(date.year)
    if detect_lang:
        d['language'], d['error'] = detect_language(soup.text)
    return d


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("langid").setLevel(logging.WARNING)
    logger = logging.getLogger()
else:
    logger = logging.getLogger(__name__)
