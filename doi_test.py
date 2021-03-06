#! /usr/bin/python
# -*- coding: utf-8 -*-

"""Test doi.py module."""


import unittest

import dummy_requests
import doi
from doi import doi_response


class DoiTest(unittest.TestCase):

    def test_doi1(self):
        i = 'https://doi.org/10.1038%2Fnrd842'
        o = doi_response(i)
        e = (
            "* {{cite journal "
            "| last=Atkins "
            "| first=Joshua H. "
            "| last2=Gershell "
            "| first2=Leland J. "
            "| title=From the analyst's couch: Selective anticancer drugs "
            "| journal=Nature Reviews Drug Discovery "
            "| publisher=Springer Nature "
            "| volume=1 "
            "| issue=7 "
            "| year=2002 "
            "| pages=491–492 "
            "| url=https://doi.org/10.1038%2Fnrd842 "
            "| doi=10.1038/nrd842 "
            "| ref=harv "
            "| accessdate="
        )
        self.assertIn(e, o.cite)

    def test_doi2(self):
        """Title of this DOI could not be detected in an older version."""
        i = 'http://www.jstor.org/stable/info/10.1086/677379'
        o = doi_response(i)
        e = (
            '* {{cite journal '
            '| title=Books of Critical Interest '
            '| journal=Critical Inquiry '
            '| publisher=University of Chicago Press '
            '| volume=40 '
            '| issue=3 '
            '| year=2014 '
            '| pages=272–281 '
            '| url=https://doi.org/10.1086%2F677379 '
            '| doi=10.1086/677379 '
            '| ref={{sfnref '
            '| University of Chicago Press | 2014}} '
            '| accessdate='
        )
        self.assertIn(e, o.cite)

    def test_doi3(self):
        """No author. URL contains %2F."""
        i = 'https://doi.org/10.1037%2Fh0063404'
        o = doi_response(i)
        e = (
            '* {{cite journal '
            '| last=Spitzer '
            '| first=H. F. '
            '| title=Studies in retention. '
            '| journal=Journal of Educational Psychology '
            '| publisher=American Psychological Association (APA) '
            '| volume=30 '
            '| issue=9 '
            '| year=1939 '
            '| pages=641–656 '
            '| url=https://doi.org/10.1037%2Fh0063404 '
            '| doi=10.1037/h0063404 '
            '| ref=harv '
            '| accessdate='
        )
        self.assertIn(e, o.cite)

    def test_doi4(self):
        """publisher=Informa {UK"""
        i = '10.1081%2Fada-200068110'
        o = doi_response(i)
        e = (
            '* {{cite journal '
            '| last=Davis '
            '| first=Margaret I. '
            '| last2=Jason '
            '| first2=Leonard A. '
            '| last3=Ferrari '
            '| first3=Joseph R. '
            '| last4=Olson '
            '| first4=Bradley D. '
            '| last5=Alvarez '
            '| first5=Josefina '
            '| title=A Collaborative Action Approach to Researching '
            'Substance Abuse Recovery '
            '| journal=The American Journal of Drug and Alcohol Abuse '
            '| publisher=Informa UK Limited '
            '| volume=31 '
            '| issue=4 '
            '| year=2005 '
            '| pages=537–553 '
            '| url=https://doi.org/10.1081%2Fada-200068110 '
            '| doi=10.1081/ada-200068110 '
            '| ref=harv '
            '| accessdate='
        )
        self.assertIn(e, o.cite)


doi.requests_get = dummy_requests.DummyRequests().get
if __name__ == '__main__':
    unittest.main()
