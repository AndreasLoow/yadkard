#! /usr/bin/python
# -*- coding: utf-8 -*-

"""Codes specifically related to ISBNs."""

import re
from threading import Thread

from requests import get as requests_get

from adinebook import url2dictionary as adinebook_url2dictionary
from adinebook import isbn2url as adinebook_isbn2url
from bibtex import parse as bibtex_parse
from commons import dictionary_to_response, detect_language, Response


# original regex from: https://www.debuggex.com/r/0Npla56ipD5aeTr9
ISBN13_SEARCH = re.compile(
    r'97(?:8|9)([ -]?)(?=\d{1,5}\1?\d{1,7}\1?\d{1,6}\1?\d)(?:\d\1*){9}\d'
).search

# original regex from: https://www.debuggex.com/r/2s3Wld3CVCR1wKoZ
ISBN10_SEARCH = re.compile(
    r'(?=\d{1,5}([ -]?)\d{1,7}\1?\d{1,6}\1?\d)(?:\d\1*){9}[\dX]'
).search

# original regex from: http://stackoverflow.com/a/14260708/2705757
# ISBN_REGEX = re.compile(
#     r'(?=[-0-9 ]{17}|[-0-9X ]{13}|[0-9X]{10})(?:97[89][- ]?)'
#     r'?[0-9]{1,5}[- ]?(?:[0-9]+[- ]?){2}[0-9X]'
# )

OTTOBIB_SEARCH = re.compile('<textarea.*>(.*)</textarea>', re.DOTALL).search


class IsbnError(Exception):

    """Raise when bibliographic information is not available."""

    pass


def isbn_response(
    isbn_container_str: str, pure: bool=False, date_format: str='%Y-%m-%d'
) -> Response:
    """Create the response namedtuple."""
    if pure:
        isbn = isbn_container_str
    else:
        # search for isbn13
        m = ISBN13_SEARCH(isbn_container_str)
        if m:
            isbn = m.group(0)
        else:
            # search for isbn10
            m = ISBN10_SEARCH(isbn_container_str)
            isbn = m.group(0)
    adinebook_dict_list = []
    thread = Thread(
        target=adinebook_thread,
        args=(isbn, adinebook_dict_list),
    )
    thread.start()
    ottobib_bibtex = ottobib(isbn)
    if ottobib_bibtex:
        otto_dict = bibtex_parse(ottobib_bibtex)
    else:
        otto_dict = None
    thread.join()
    if adinebook_dict_list:
        adine_dict = adinebook_dict_list.pop()
    else:
        adine_dict = None
    dictionary = choose_dict(adine_dict, otto_dict)
    dictionary['date_format'] = date_format
    if 'language' not in dictionary:
        dictionary['language'], dictionary['error'] = \
            detect_language(dictionary['title'])
    return dictionary_to_response(dictionary)


def adinebook_thread(isbn, result_list):
    """Add the dictionary generated by adinebook module to the result_list."""
    result_list.append(
        adinebook_url2dictionary(
            adinebook_isbn2url(isbn)
        )
    )


def choose_dict(adine_dict, otto_dict):
    """Choose which source to use.

    Return adinebook if both contain the same ISBN or if adinebook is None,
    else return ottobib.
    
    Background: adinebook.com ommits 3 digits from it's isbn when converting
    them to URLs. This may make them volnarable to resolving into wrong ISBN.
    """
    if not otto_dict and not adine_dict:
        raise IsbnError('Bibliographic information not found.')
    elif adine_dict and otto_dict:
        # both exist
        if isbn2int(adine_dict['isbn']) == isbn2int(otto_dict['isbn']):
            # both isbns are equal
            return adine_dict
        else:
            # isbns are not equal
            return otto_dict
    elif adine_dict:
        # only adinebook exists
        return adine_dict
    else:
        # only ottobib exists
        return otto_dict


def isbn2int(isbn):
    """Get ISBN string and return it as in integer."""
    return int(isbn.replace('-', '').replace(' ', ''))


def ottobib(isbn):
    """Convert ISBN to bibtex using ottobib.com."""
    m = OTTOBIB_SEARCH(
        requests_get('http://www.ottobib.com/isbn/' + isbn + '/bibtex').text
    )
    if m:
        return m.group(1)
