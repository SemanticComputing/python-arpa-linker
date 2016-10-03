import logging
import unittest
import doctest
import persons
import os
import sys
from unittest import TestCase
from datetime import date
from rdflib import Graph, URIRef

from persons import Validator, ValidationContext, pruner, preprocessor, MANNERHEIM_RITARIT


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


class TestPersonValidation(TestCase):

    def setUp(self):
        ValidationContext.dataset = 'photo'
        g = Graph()
        f = os.path.join(sys.path[0], 'test_photo_person.ttl')
        g.parse(f, format='turtle')
        self.validator = Validator(g)

    def test_get_ranked_matches(self):
        props = {'death_date': ['"1944-09-02"^^xsd:date'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Komppaniaupseeri"'],
                'rank': ['"Vänrikki"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'lieutenant'}
        props2 = {'death_date': ['"1942-04-28"^^xsd:date'],
                'promotion_date': ['"1942-04-26"^^xsd:date'],
                'hierarchy': ['"Kenraalikunta"'],
                'rank': ['"Kenraalimajuri"']}
        person2 = {'properties': props2, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'general'}
        results = [person, person2]
        ctx = ValidationContext(self.validator.graph, results, None)
        rd = ctx.ranked_matches

        self.assertEqual(rd['A. Snellman']['uris'], {'lieutenant'})
        self.assertEqual(rd['A. Snellman']['score'], -20)
        self.assertEqual(rd['Kenraalimajuri A. Snellman']['uris'], {'general'})
        self.assertEqual(rd['Kenraalimajuri A. Snellman']['score'], 0)

        person2 = {'properties': props, 'matches': ['A. Snellman'], 'id': 'general'}
        results = [person, person2]
        ctx = ValidationContext(self.validator.graph, results, None)
        rd = ctx.ranked_matches

        self.assertEqual(len(rd), 1)
        self.assertTrue('lieutenant' in rd['A. Snellman']['uris'])
        self.assertTrue('general' in rd['A. Snellman']['uris'])
        self.assertEqual(rd['A. Snellman']['score'], 0)

    def test_get_current_rank(self):
        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-04-01"^^xsd:date'],
        'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        person = {'properties': ranks}
        d = date(1940, 3, 5)

        self.assertEqual(self.validator.get_current_rank(person, d), 'Korpraali')

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-04-01"^^xsd:date'],
        'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        person = {'properties': ranks}
        d = date(1940, 4, 5)

        self.assertEqual(self.validator.get_current_rank(person, d), 'Luutnantti')

    def test_has_consistent_rank(self):
        props = {'hierarchy': ['"Kenraalikunta"'],
        'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id'}

        self.assertFalse(self.validator.has_consistent_rank(person, "sotamies A. Snellman"))

        props = {'hierarchy': ['"Kenraalikunta"'],
        'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['kenraalikunta Snellman'], 'id': 'id'}

        self.assertTrue(self.validator.has_consistent_rank(person, "kenraalikunta Snellman"))

        props = {'hierarchy': ['"Kenraalikunta"'],
        'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id'}

        self.assertFalse(self.validator.has_consistent_rank(person, "sotamies E. A. Snellman"))

        props = {'hierarchy': ['"Kenraalikunta"'],
        'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['Aarne Snellman'], 'id': 'id'}

        self.assertFalse(self.validator.has_consistent_rank(person, "sotamies Turo Aarne Snellman"))

        props = {'hierarchy': ['"Kenraalikunta"'],
        'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['kenraalikunta Snellman'], 'id': 'id'}

        self.assertTrue(self.validator.has_consistent_rank(person, "sotamies Turtti kenraalikunta Snellman"))

        props = {'hierarchy': ['"Kenraalikunta"'],
        'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id'}

        self.assertTrue(self.validator.has_consistent_rank(person, "sotamies Turtti kenraalikunta A. Snellman"))

        props = {'hierarchy': ['"Kenraalikunta"'],
        'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id'}

        self.assertFalse(self.validator.has_consistent_rank(person, "sotamies Turtti A. Snellman"))

        person = {'properties': props, 'matches': ['kenraalikunta A. Snellman', 'A. Snellman'], 'id': 'id'}

        self.assertTrue(self.validator.has_consistent_rank(person, "kenraalikunta A. Snellman"))

        # This is a bit unfortunate, but it shouldn't be a problem.
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id'}

        self.assertFalse(self.validator.has_consistent_rank(person, "upseeri A. Snellman"))

        props = {'hierarchy': ['"Miehistö"'],
        'rank': ['"Sotamies"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id'}

        self.assertFalse(self.validator.has_consistent_rank(person, "kenraalikunta A. Snellman"))

    def test_get_match_scores(self):
        props = {'death_date': ['"1944-09-02"^^xsd:date'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Komppaniaupseeri"'],
                'rank': ['"Vänrikki"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'lieutenant'}
        props2 = {'death_date': ['"1942-04-28"^^xsd:date'],
                'promotion_date': ['"1942-04-26"^^xsd:date'],
                'hierarchy': ['"Kenraalikunta"'],
                'rank': ['"Kenraalimajuri"']}
        person2 = {'properties': props2, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'general'}
        results = [person, person2]
        ctx = ValidationContext(self.validator.graph, results, None)
        scores = ctx.get_match_scores(results)

        self.assertEqual(scores['general'], 0)
        self.assertEqual(scores['lieutenant'], -20)

        props = {'death_date': ['"1942-04-28"^^xsd:date'],
                'promotion_date': ['"1942-04-26"^^xsd:date'],
                'hierarchy': ['"Kenraalikunta"'],
                'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'general2'}
        results = [person, person2]
        ctx = ValidationContext(self.validator.graph, results, None)
        scores = ctx.get_match_scores(results)

        self.assertEqual(scores['general'], 0)
        self.assertEqual(scores['general2'], 0)

        props = {'death_date': ['"1944-06-30"^^xsd:date'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'rank': ['"Sotamies"']}
        person = {'properties': props, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id1'}
        props2 = {'death_date': ['"1943-09-22"^^xsd:date'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'rank': ['"Sotamies"']}
        person2 = {'properties': props2, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id2'}
        props3 = {'death_date': ['"1940-02-02"^^xsd:date'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'rank': ['"Sotamies"']}
        person3 = {'properties': props3, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id3'}
        results = [person, person2, person3]
        ctx = ValidationContext(self.validator.graph, results, None)
        scores = ctx.get_match_scores(results)

        self.assertEqual(scores['id1'], 0)
        self.assertEqual(scores['id2'], 0)
        self.assertEqual(scores['id3'], 0)

    def test_get_fuzzy_current_ranks(self):
        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-04-06"^^xsd:date'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-04-06"^^xsd:date'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        person = {'properties': ranks}
        d = date(1940, 3, 5)
        r = self.validator.get_fuzzy_current_ranks(person, d, 'rank', 0)
        self.assertEqual(len(r), 1)
        self.assertTrue('Korpraali' in r)

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        person = {'properties': ranks, 'matches': ['kenraalikunta Karpalo']}
        d = date(1941, 3, 5)
        r = self.validator.get_fuzzy_current_ranks(person, d, 'hierarchy', 0)

        self.assertEqual(len(r), 1)
        self.assertTrue('Kenraalikunta' in r)

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-04-06"^^xsd:date'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-04-06"^^xsd:date'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        person = {'properties': ranks}
        d = date(1940, 3, 5)
        r = self.validator.get_fuzzy_current_ranks(person, d, 'rank')

        self.assertEqual(len(r), 2)
        self.assertTrue('Korpraali' in r)
        self.assertTrue('Sotamies' in r)

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        person = {'properties': ranks}
        d = date(1943, 4, 5)

        self.assertEqual(self.validator.get_fuzzy_current_ranks(person, d, 'rank'), {'Luutnantti'})

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Yleisesikuntaupseeri"']}
        person = {'properties': ranks}
        d = date(1943, 4, 5)

        self.assertEqual(self.validator.get_fuzzy_current_ranks(person, d, 'rank'), {'Korpraali'})

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'latest_promotion_date': ['"1940-05-01"^^xsd:date', '"1940-05-01"^^xsd:date', '"1941-05-01"^^xsd:date'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        person = {'properties': ranks}
        d = date(1943, 4, 5)

        self.assertEqual(self.validator.get_fuzzy_current_ranks(person, d, 'rank'), {'Luutnantti'})

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-03-01"^^xsd:date'],
                'latest_promotion_date': ['"1940-05-01"^^xsd:date', '"1940-05-01"^^xsd:date', '"1940-05-01"^^xsd:date'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        person = {'properties': ranks}
        d = date(1943, 4, 5)
        r = self.validator.get_fuzzy_current_ranks(person, d, 'rank')

        self.assertEqual(len(r), 3)

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-04-22"^^xsd:date', '"1940-04-22"^^xsd:date'],
                'latest_promotion_date': ['"1940-04-21"^^xsd:date', '"1940-05-01"^^xsd:date', '"1940-05-01"^^xsd:date'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        person = {'properties': ranks}
        d = date(1943, 4, 5)
        r = self.validator.get_fuzzy_current_ranks(person, d, 'rank')

        self.assertEqual(len(r), 2)

    def test_ranks_with_unknown_date(self):
        props = {'death_date': ['"1976-09-02"^^xsd:date'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Aliupseeri"'],
                'rank': ['"Lentomestari"']}
        person = {'properties': props, 'matches': ['lentomestari Oiva Tuominen', 'Oiva Tuominen'], 'id': 'id1'}

        self.assertEqual(self.validator.get_ranks_with_unknown_date(person, 'rank'), ['Lentomestari'])

        ranks = {'promotion_date': ['"NA"'],
                'hierarchy': ['"NA"'],
                'rank': ['"NA"']}
        person = {'properties': ranks, 'matches': ['Adolf Hitler']}

        self.assertEqual(self.validator.get_ranks_with_unknown_date(person, 'rank'), ['NA'])

        props = {'promotion_date': ['"NA"', '"1976-09-02"^^xsd:date'],
                'hierarchy': ['"Aliupseeri"', '"Kenraalikunta"'],
                'rank': ['"Lentomestari"', '"Kenraali"']}
        person = {'properties': props, 'matches': ['lentomestari Oiva Tuominen', 'Oiva Tuominen'], 'id': 'id1'}

        self.assertEqual(self.validator.get_ranks_with_unknown_date(person, 'rank'), ['Lentomestari'])

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"NA"'],
                'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        person = {'properties': ranks, 'matches': ['kenraalikunta Karpalo']}

        self.assertEqual(self.validator.get_ranks_with_unknown_date(person, 'hierarchy'), ['Kenraalikunta'])

    def test_get_rank_score(self):
        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        person = {'properties': ranks, 'matches': ['Kenraali Karpalo']}

        self.assertEqual(self.validator.get_rank_score(person, date(1941, 3, 5), "Kenraali Karpalo"), 21)
        self.assertEqual(self.validator.get_rank_score(person, date(1940, 3, 5), "Kenraali Karpalo"), -14)

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1946-03-01"^^xsd:date'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1946-03-01"^^xsd:date'],
                'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        person = {'properties': ranks, 'matches': ['kenraali Karpalo']}

        self.assertEqual(self.validator.get_rank_score(person, None, "kenraali Karpalo"), -14)

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        person = {'properties': ranks, 'matches': ['kenraalikunta Karpalo']}

        self.assertEqual(self.validator.get_rank_score(
            person, date(1941, 3, 5), "kenraalikunta Karpalo"), 21)
        self.assertEqual(self.validator.get_rank_score(person, None, "kenraalikunta Karpalo"), 11)

        ranks = {'promotion_date': ['"NA"'],
                'latest_promotion_date': ['"NA"'],
                'hierarchy': ['"NA"'],
                'rank': ['"NA"']}
        person = {'properties': ranks, 'matches': ['Adolf Hitler']}

        self.assertEqual(self.validator.get_rank_score(person, date(1941, 3, 5), "Adolf Hitler"), 0)

        ranks = {'promotion_date': ['"NA"'],
                'latest_promotion_date': ['"NA"'],
                'hierarchy': ['"NA"'],
                'rank': ['"NA"']}
        person = {'properties': ranks, 'matches': ['Jorma Sarvanto']}

        self.assertEqual(self.validator.get_rank_score(person, date(1941, 3, 5), "luutnantti Jorma Sarvanto"), 0)

        ranks = {'promotion_date': ['"NA"', '"NA"'],
                'latest_promotion_date': ['"NA"', '"NA"'],
                'hierarchy': ['"Aliupseeri"', '"virkahenkilostö"'],
                'rank': ['"Alikersantti"', '"Sotilasvirkamies"']}
        person = {'properties': ranks, 'matches': ['Kari Suomalainen']}

        self.assertEqual(self.validator.get_rank_score(person, date(1941, 3, 5), "Piirros: Kari Suomalainen"), 0)

        ranks = {'promotion_date': ['"NA"'],
                'latest_promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'rank': ['"Sotamies"']}
        person = {'properties': ranks, 'matches': ['Jorma Sarvanto']}

        self.assertEqual(self.validator.get_rank_score(person, date(1941, 3, 5), "luutnantti Jorma Sarvanto"), -10)

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"NA"'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"NA"'],
                'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        person = {'properties': ranks, 'matches': ['kenraalikunta Karpalo']}

        self.assertEqual(self.validator.get_rank_score(person, date(1941, 3, 5), "kenraalikunta Karpalo"), 11)

        ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"NA"'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"NA"'],
                'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        person = {'properties': ranks, 'matches': ['kenraali Karpalo']}

        self.assertEqual(self.validator.get_rank_score(person, date(1941, 3, 5), "kenraali Karpalo"), 11)

    def test_get_date_score(self):
        props = {'death_date': ['"1940-02-01"^^xsd:date', '"1940-02-01"^^xsd:date',
            '"1940-03-01"^^xsd:date']}
        person = {'properties': props}

        self.assertEqual(self.validator.get_date_score(person, date(1941, 3, 5), None, None), -30)

        props = {'death_date': ['"1940-02-01"^^xsd:date', '"1940-02-01"^^xsd:date',
            '"1940-03-01"^^xsd:date']}
        person = {'properties': props}

        self.assertEqual(self.validator.get_date_score(person, date(1939, 3, 5), None, None), 0)
        self.assertEqual(self.validator.get_date_score(person, None, None, None), 0)

        props = {}
        person = {'properties': props}

        self.assertEqual(self.validator.get_date_score(person, date(1939, 3, 5), None, None), 0)

    def test_get_name_score(self):
        person = {'properties': {'first_names': ['"Turo Tero"']}, 'matches': ['kenraali Karpalo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), -5)

        person = {'properties': {'first_names': ['"Turo Tero"']}, 'matches': ['Tero Karpalo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), 5)

        person = {'properties': {'first_names': ['"Turo Tero"']}, 'matches': ['Turo Karpalo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), 10)

        person = {'properties': {'first_names': ['"Turo"']}, 'matches': ['Turo Karpalo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), 10)

        person = {'properties': {'first_names': ['"Turo Jare"']}, 'matches': ['T. J. Karpalo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), 5)

        person = {'properties': {'first_names': ['"Turo Jare"']}, 'matches': ['T.J. Karpalo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), 5)

        person = {'properties': {'first_names': ['"Turo Jare"']}, 'matches': ['T.J.Karpalo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), 5)

        person = {'properties': {'first_names': ['"Turo Jare"']}, 'matches': ['Korpraali T.J.Karpalo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), 5)

        person = {'properties': {'first_names': ['"Turo Jare"']}, 'matches': ['Korpraali T.Karpalo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), -5)

        person = {'properties': {'first_names': ['"Viljo Wiljo Einar"']}, 'matches': ['W.E.Tuompo'], 'id': 'id'}

        self.assertEqual(self.validator.get_name_score(person), -5)

    def test_get_source_score(self):
        props = {'source': ['<http://ldf.fi/warsa/sources/source5>']}
        person = {'properties': props, 'id': 'id'}

        self.assertEqual(self.validator.get_source_score(person), 1)

        props = {'source': ['<http://ldf.fi/warsa/sources/source1>']}
        person = {'properties': props, 'id': 'id'}

        self.assertEqual(self.validator.get_source_score(person), 0)

        props = {'source': ['na']}
        person = {'properties': props, 'id': 'id'}

        self.assertEqual(self.validator.get_source_score(person), 0)

        props = {}
        person = {'properties': props, 'id': 'id'}

        self.assertEqual(self.validator.get_source_score(person), 0)

    def test_get_unit_score(self):
        unit = '<http://ldf.fi/warsa/actors/actor_2942>'
        props = {'unit': [unit]}
        person = {'properties': props, 'id': 'id'}

        self.assertEqual(self.validator.get_unit_score(person, {unit}), 10)

        person['properties']['unit'] = []

        self.assertEqual(self.validator.get_unit_score(person, {unit}), 0)

        person['properties']['unit'] = ['<http://ldf.fi/warsa/actors/actor_29>']

        self.assertEqual(self.validator.get_unit_score(person, {unit}), 0)
        self.assertEqual(self.validator.get_unit_score(person, set()), 0)

    def test_get_knight_score(self):
        props = {'source': ['<http://ldf.fi/warsa/sources/source1>']}
        person = {'properties': props, 'matches': ['kenraali Karpalo'], 'id': 'id'}
        results = [person]

        ctx = ValidationContext(self.validator.graph, results, None)
        self.assertEqual(self.validator.get_knight_score(person, 'kenraali Karpalo', results, ctx.ranked_matches), 0)

        props['source'].append(MANNERHEIM_RITARIT)

        self.assertEqual(self.validator.get_knight_score(person, 'kenraali Karpalo', results, ctx.ranked_matches), 0)

        props['source'].append(MANNERHEIM_RITARIT)

        self.assertEqual(self.validator.get_knight_score(person, 'ritari kenraali Karpalo', results, ctx.ranked_matches), 20)

        props = {'source': [MANNERHEIM_RITARIT]}
        person = {'properties': props, 'matches': ['kenraali Karpalo'], 'id': 'id'}
        other_props = {'source': ['<http://ldf.fi/warsa/sources/source1>']}
        other = {'properties': other_props, 'matches': ['kenraali Karpalo'], 'id': 'id2'}
        results = [person, other]

        ctx = ValidationContext(self.validator.graph, results, None)
        self.assertEqual(self.validator.get_knight_score(person, 'ritari kenraali Karpalo', results, ctx.ranked_matches), 20)
        self.assertEqual(self.validator.get_knight_score(other, 'ritari kenraali Karpalo', results, ctx.ranked_matches), -20)

        props = {'death_date': ['"1944-09-02"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Komppaniaupseeri"'],
                'source': [MANNERHEIM_RITARIT],
                'rank': ['"Vänrikki"']}
        props2 = {'death_date': ['"1942-04-28"^^xsd:date'],
                'latest_promotion_date': ['"1942-04-26"^^xsd:date'],
                'promotion_date': ['"1942-04-26"^^xsd:date'],
                'hierarchy': ['"Kenraalikunta"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id1'}
        person2 = {'properties': props2, 'matches': ['A. Snellman'], 'id': 'id2'}
        results = [person, person2]

        ctx = ValidationContext(self.validator.graph, results, None)
        self.assertEqual(self.validator.get_knight_score(person, 'ritari A. Snellman', results, ctx.ranked_matches), 20)
        self.assertEqual(self.validator.get_knight_score(person2, 'ritari A. Snellman', results, ctx.ranked_matches), -20)

        person2 = {'properties': props2, 'matches': ['kenraalikunta A. Snellman', 'A. Snellman'], 'id': 'id2'}
        results = [person, person2]

        ctx = ValidationContext(self.validator.graph, results, None)
        self.assertEqual(self.validator.get_knight_score(person2, 'ritari kenraalikunta A. Snellman', results, ctx.ranked_matches), 0)

    def test_get_score(self):
        props = {'death_date': ['"1942-02-01"^^xsd:date', '"1942-02-01"^^xsd:date', '"1942-03-01"^^xsd:date'],
                'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'latest_promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
                'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        person = {'properties': props, 'matches': ['kenraali Karpalo'], 'id': 'id'}
        results = [person]
        s = URIRef('http://ldf.fi/warsa/photographs/sakuva_1000')
        ctx = ValidationContext(self.validator.graph, results, s)

        self.assertEqual(self.validator.get_score(person, 'kenraali Karpalo', ctx), 21)

        props = {'death_date': ['"1945-04-30"^^xsd:date', '"1945-04-30"^^xsd:date', '"1945-04-30"^^xsd:date'],
                'first_names': ['"Adolf"', '"Adolf"'],
                'promotion_date': ['"NA"', '"NA"', '"NA"'],
                'latest_promotion_date': ['"NA"', '"NA"', '"NA"'],
                'hierarchy': ['"NA"', '"NA"', '"NA"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"NA"', '"NA"', '"NA"']}
        person = {'properties': props, 'matches': ['Adolf Hitler'], 'id': 'id'}
        results = [person]

        ctx = ValidationContext(self.validator.graph, results, s)
        ctx.s_date = date(1941, 3, 5)
        self.assertEqual(self.validator.get_score(person, 'Adolf Hitler', ctx), 10)

        props = {'death_date': ['"1944-09-02"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Komppaniaupseeri"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Vänrikki"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id1'}
        props2 = {'death_date': ['"1942-04-28"^^xsd:date'],
                'latest_promotion_date': ['"1942-04-26"^^xsd:date'],
                'promotion_date': ['"1942-04-26"^^xsd:date'],
                'hierarchy': ['"Kenraalikunta"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Kenraalimajuri"']}
        person2 = {'properties': props2, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'id2'}
        results = [person, person2]

        ctx = ValidationContext(self.validator.graph, results, s)
        ctx.s_date = date(1942, 4, 27)
        self.assertEqual(self.validator.get_score(person, 'Kenraalimajuri A. Snellman', ctx), -30)
        self.assertEqual(self.validator.get_score(person2, 'Kenraalimajuri A. Snellman', ctx), 21)

        props = {'death_date': ['"1942-04-28"^^xsd:date'],
                'latest_promotion_date': ['"1942-04-26"^^xsd:date'],
                'promotion_date': ['"1942-04-26"^^xsd:date'],
                'hierarchy': ['"Kenraalikunta"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'id'}
        results = [person]

        ctx = ValidationContext(self.validator.graph, results, s)
        ctx.s_date = date(1941, 11, 20)
        self.assertEqual(self.validator.get_score(person, 'Kenraalimajuri A. Snellman', ctx), -14)

        props = {'death_date': ['"1976-09-02"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Aliupseeri"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Lentomestari"']}
        person = {'properties': props, 'matches': ['lentomestari Oiva Tuominen', 'Oiva Tuominen'], 'id': 'id1'}
        props2 = {'death_date': ['"1944-04-28"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Korpraali"']}
        person2 = {'properties': props2, 'matches': ['Oiva Tuominen'], 'id': 'id2'}
        props3 = {'death_date': ['"1940-04-28"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Sotamies"']}
        person3 = {'properties': props3, 'matches': ['Oiva Tuominen'], 'id': 'id3'}
        results = [person, person2, person3]

        ctx = ValidationContext(self.validator.graph, results, s)
        ctx.s_date = date(1942, 4, 27)
        self.assertEqual(self.validator.get_score(person, 'lentomestari Oiva Tuominen', ctx), 5)
        self.assertEqual(self.validator.get_score(person2, 'lentomestari Oiva Tuominen', ctx), -30)
        self.assertEqual(self.validator.get_score(person3, 'lentomestari Oiva Tuominen', ctx), -60)

        props = {'death_date': ['"1944-06-30"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'first_names': ['Arvi Petteri'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Sotamies"']}
        person = {'properties': props, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id1'}
        props2 = {'death_date': ['"1943-09-22"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'first_names': ['Petteri'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Sotamies"']}
        person2 = {'properties': props2, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id2'}
        props3 = {'death_date': ['"1940-02-02"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'first_names': ['Petteri Arvi'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Sotamies"']}
        person3 = {'properties': props3, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id3'}
        results = [person, person2, person3]

        ctx = ValidationContext(self.validator.graph, results, s)
        ctx.s_date = date(1944, 5, 31)
        self.assertEqual(self.validator.get_score(person, 'sotamies Arvi Pesonen', ctx), 10)
        self.assertEqual(self.validator.get_score(person2, 'sotamies Arvi Pesonen', ctx), -35)
        self.assertEqual(self.validator.get_score(person3, 'sotamies Arvi Pesonen', ctx), -25)

        props = {'death_date': ['"1944-06-15"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'first_names': ['"Tuomas"'],
                'family_name': ['"Noponen"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Korpraali"']}
        person = {'properties': props, 'matches': ['Tuomas Noponen'], 'id': 'id1'}
        results = [person]

        ctx = ValidationContext(self.validator.graph, results, s)
        ctx.s_date = date(1941, 8, 4)
        self.assertEqual(self.validator.get_score(person, 'Tuomas Noponen', ctx), 0)

        props = {'death_date': ['"1999-08-10"^^xsd:date', '"1999-08-10"^^xsd:date'],
                'latest_promotion_date': ['"NA"', '"NA"'],
                'promotion_date': ['"NA"', '"NA"'],
                'first_names': ['"Kari"', '"Kari"'],
                'family_name': ['"SUOMALAINEN"', '"SUOMALAINEN"'],
                'hierarchy': ['"Aliupseeri"', '"virkahenkilostö"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Alikersantti"', '"Sotilasvirkamies"']}
        person = {'properties': props, 'matches': ['Kari Suomalainen'], 'id': 'id'}
        results = [person]

        ctx = ValidationContext(self.validator.graph, results, s)
        ctx.s_date = date(1941, 3, 5)
        self.assertEqual(self.validator.get_score(person, 'Piirros Kari Suomalainen', ctx), 10)

        props = {'promotion_date': ['"NA"', '"NA"'],
                'latest_promotion_date': ['"NA"', '"NA"'],
                'hierarchy': ['"NA"', '"NA"'],
                'family_name': ['"Hämäläinen"', '"Hämäläinen"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Reservin vänrikki"', '"Reservin vänrikki"']}
        person = {'properties': props, 'matches': ['Reservin vänrikki Hämäläinen', 'vänrikki Hämäläinen'],
                'id': 'id1'}
        results = [person]

        ctx = ValidationContext(self.validator.graph, results, s)
        ctx.s_date = date(1941, 8, 4)
        self.assertEqual(self.validator.get_score(person, 'Reservin vänrikki Hämäläinen', ctx), 10)

        props = {'death_date': ['"1971-10-10"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"NA"'],
                'first_names': ['"Yrjö"'],
                'family_name': ['"Pöyhönen"'],
                'source': ['<http://ldf.fi/warsa/sources/source10>'],
                'rank': ['"NA"']}
        person = {'properties': props, 'matches': ['Y. Pöyhönen'], 'id': 'id1'}
        results = [person]

        ctx = ValidationContext(self.validator.graph, results, s)
        self.assertEqual(self.validator.get_score(person, 'everstiluutnantti Y. Pöyhönen', ctx), -4)

        props = {'death_date': ['"1942-10-10"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'first_names': ['"Kalle"'],
                'family_name': ['"Sukunimi"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Sotamies"']}
        person = {'properties': props, 'matches': ['sotamies Sukunimi'], 'id': 'id1'}
        results = [person]

        ctx = ValidationContext(self.validator.graph, results, s)
        self.assertEqual(self.validator.get_score(person, 'sotamies Sukunimi', ctx), -5)

        props = {'death_date': ['"1944-06-15"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Miehistö"'],
                'first_names': ['"Tuomas"'],
                'family_name': ['"Noponen"'],
                'source': [MANNERHEIM_RITARIT],
                'rank': ['"Korpraali"']}
        person = {'properties': props, 'matches': ['Tuomas Noponen'], 'id': 'id1'}
        results = [person]

        ctx = ValidationContext(self.validator.graph, results, URIRef('http://ldf.fi/warsa/photographs/sakuva_1000'))
        self.assertEqual(self.validator.get_score(person, 'Tuomas Noponen', ctx), 1)
        ctx = ValidationContext(self.validator.graph, results, URIRef('http://ldf.fi/warsa/photographs/sakuva_127026_test'))
        self.assertEqual(self.validator.get_score(person, 'Tuomas Noponen', ctx), 21)

        props = {'death_date': ['"1944-09-02"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Komppaniaupseeri"'],
                'source': [MANNERHEIM_RITARIT],
                'rank': ['"Vänrikki"']}
        props2 = {'death_date': ['"1942-04-28"^^xsd:date'],
                'latest_promotion_date': ['"1942-04-26"^^xsd:date'],
                'promotion_date': ['"1942-04-26"^^xsd:date'],
                'hierarchy': ['"Kenraalikunta"'],
                'source': ['<http://ldf.fi/warsa/sources/source1>'],
                'rank': ['"Kenraalimajuri"']}
        person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id1'}
        person2 = {'properties': props2, 'matches': ['A. Snellman'], 'id': 'id2'}
        results = [person, person2]

        ctx = ValidationContext(self.validator.graph, results, URIRef('http://ldf.fi/warsa/photographs/sakuva_127026_test'))
        ctx.s_date = date(1942, 4, 27)
        self.assertEqual(self.validator.get_score(person, 'A. Snellman', ctx), 21)
        self.assertEqual(self.validator.get_score(person2, 'A. Snellman', ctx), -19)

        person2 = {'properties': props2, 'matches': ['kenraalikunta A. Snellman', 'A. Snellman'], 'id': 'id2'}
        results = [person, person2]

        ctx = ValidationContext(self.validator.graph, results, URIRef('http://ldf.fi/warsa/photographs/sakuva_127026_test'))
        ctx.s_date = date(1942, 4, 27)
        self.assertEqual(self.validator.get_score(person2, 'kenraalikunta A. Snellman', ctx), 21)
        self.assertEqual(self.validator.get_score(person, 'kenraalikunta A. Snellman', ctx), -9)

    def test_overall_score_with_unit(self):
        unit = '<http://ldf.fi/warsa/actors/actor_2747>'
        props = {'death_date': ['"1942-02-07"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Aliupseeri"'],
                'first_names': ['"Reino"'],
                'family_name': ['"Leskinen"'],
                'unit': [unit],
                'rank': ['"Kersantti"']}
        props2 = {'death_date': ['"1944-07-27"^^xsd:date'],
                'latest_promotion_date': ['"NA"'],
                'promotion_date': ['"NA"'],
                'hierarchy': ['"Aliupseeri"'],
                'first_names': ['"Pauli"'],
                'family_name': ['"Leskinen"'],
                'unit': ['<http://ldf.fi/warsa/actors/actor_2509>'],
                'rank': ['"Kersantti"']}
        reino = {'properties': props, 'matches': ['kersantti Leskinen'], 'id': 'id1'}
        pauli = {'properties': props2, 'matches': ['kersantti Leskinen'], 'id': 'id2'}
        results = [reino, pauli]
        ctx = ValidationContext(self.validator.graph, results, URIRef('http://ldf.fi/warsa/photographs/sakuva_74965'))
        self.assertEqual(self.validator.get_score(reino, '"kersantti Leskinen"', ctx), 10)
        self.assertEqual(self.validator.get_score(pauli, '"kersantti Leskinen"', ctx), 0)

    def test_preprocessor(self):
        self.assertEqual(preprocessor("Kuva ruokailusta. Ruokailussa läsnä: Kenraalimajuri Martola, "
            "ministerit: Koivisto, Salovaara, Horelli, Arola, hal.neuv. Honka, "
            "everstiluutnantit: Varis, Ehnrooth, Juva, Heimolainen, Björnström, "
            "majurit: Müller, Pennanen, Kalpamaa, Varko."),
            'Kuva ruokailusta. Ruokailussa läsnä: kenraalimajuri Martola, '
            'Juho Koivisto, ministeri Salovaara, ministeri Horelli, ministeri Arola, ministeri Honka, '
            'everstiluutnantti Varis, everstiluutnantti Ehnrooth, everstiluutnantti Juva, '
            'everstiluutnantti Heimolainen, everstiluutnantti Björnström, '
            'majuri Müller, majuri Pennanen, majuri Kalpamaa, majuri Varko.')
        self.assertEqual(preprocessor("Kenraali Hägglund seuraa maastoammuntaa Aunuksen kannaksen mestaruuskilpailuissa."), 'kenraalikunta Hägglund seuraa maastoammuntaa Aunuksen kannaksen mestaruuskilpailuissa.')
        self.assertEqual(preprocessor("Kenraali Karl Oesch seuraa maastoammuntaa."), 'kenraalikunta Karl Oesch seuraa maastoammuntaa.')
        self.assertEqual(preprocessor("Korkeaa upseeristoa maastoammunnan Aunuksen kannaksen mestaruuskilpailuissa."), 'Korkeaa upseeristoa maastoammunnan Aunuksen kannaksen mestaruuskilpailuissa.')
        self.assertEqual(preprocessor("Presidentti Ryti, sotamarsalkka Mannerheim, pääministeri, "
                    "kenraalit Neuvonen,Walden,Mäkinen, eversti Sihvo, kenraali Airo,Oesch, eversti Hersalo ym. klo 12.45."),
                'Risto Ryti, sotamarsalkka Mannerheim, pääministeri, kenraalikunta Neuvonen, kenraalikunta Walden, kenraalikunta Mäkinen, eversti Sihvo, kenraalikunta Airo, kenraalikunta Oesch, '
                'eversti Hersalo ym. klo 12.45.')
        self.assertEqual(preprocessor("Sotamarsalkka Raasulissa."), '# kenraalikunta Mannerheim # Raasulissa.')
        self.assertEqual(preprocessor("Eräs Brewster-koneista, jotka seurasivat marsalkan seuruetta."), 'Eräs Brewster-koneista, jotka seurasivat # kenraalikunta Mannerheim # seuruetta.')
        self.assertEqual(preprocessor("Kenraali Walden Marsalkan junassa aterialla."), 'kenraalikunta Walden # kenraalikunta Mannerheim # junassa aterialla.')
        self.assertEqual(preprocessor('"Eläköön Sotamarsalkka"'), 'Eläköön # kenraalikunta Mannerheim #')
        self.assertEqual(preprocessor("Fältmarsalk Mannerheim mattager Hangögruppens anmälar av Öv. Koskimies."),
                'sotamarsalkka Mannerheim mattager Hangögruppens anmälar av eversti Koskimies.')
        self.assertEqual(preprocessor("Majuri Laaksonen JR 8:ssa."), 'Majuri Laaksonen JR 8:ssa.')
        self.assertEqual(preprocessor("Vas: eversti Laaksonen, kapteeni Karu, ylikersantti Vorho, ja alikersantit Paajanen ja Nordin filmattavina. Oik. komentajakapteeni Arho juttelee muiden Mannerheim-ritarien kanssa."), 'Vas: eversti Laaksonen, kapteeni Karu, ylikersantti Vorho, ja alikersantti Paajanen alikersantti Nordin filmattavina. Oik. komentajakapteeni Arho juttelee muiden Mannerheim-ritarien kanssa.')
        self.assertEqual(preprocessor("Majuri Laaksosen komentopaikka mistä johdettiin viivytystaistelua Karhumäkilinjalla. Majuri Laaksonen seisomassa kuvan keskellä."), 'Majuri Laaksosen komentopaikka mistä johdettiin viivytystaistelua Karhumäkilinjalla. Majuri Laaksonen seisomassa kuvan keskellä.')
        self.assertEqual(preprocessor("Luutn. Juutilainen Saharan kauhu jouluk. Alussa."), '# kapteeni Juutilainen # # kapteeni Juutilainen # jouluk. Alussa.')
        self.assertEqual(preprocessor("Kapteenit Palolampi ja Juutilainen ratsailla Levinassa."), 'kapteeni Palolampi kapteeni Juutilainen ratsailla Levinassa.')
        self.assertEqual(preprocessor("kenraalit keskustelevat pienen tauon aikana, vas: eversti Paasonen, "
                    "kenraalimajuri Palojärvi, kenraalimajuri Svanström, Yl.Esikuntapäällikkö jalkaväenkenraali Heinrichs ja eversti Vaala."),
                'kenraalit keskustelevat pienen tauon aikana, vas: eversti Paasonen, '
                'kenraalimajuri Palojärvi, kenraalimajuri Svanström, Yl.Esikuntapäällikkö jalkaväenkenraali Heinrichs ja eversti Vaala.')
        self.assertEqual(preprocessor("Radioryhmän toimintaa: Selostaja työssään ( Vänrikki Seiva, sot.virk. Kumminen ja Westerlund)."), 'Radioryhmän toimintaa: Selostaja työssään ( vänrikki Seiva, sotilasvirkamies Kumminen sotilasvirkamies Westerlund).')
        self.assertEqual(preprocessor("TK-rintamakirjeenvaihtaja Yläjärvellä (vas. Sot.virk. Kapra, Jalkanen, vänr. Rahikainen)."), 'sotilasvirkamies Yläjärvellä (vas. sotilasvirkamies Kapra, sotilasvirkamies Jalkanen, vänrikki Rahikainen).')
        self.assertEqual(preprocessor("Ulkomaisten lehtimiesten retkikunta etulinjan komentopaikalla Tornion rintamalla 3/10-44. Komentaja, everstiluutnantti Halsti selostaa tilannetta kaistallaan piirtäen kepillä kartan maantiehen. Komentajasta oikealla: Björnsson Mehlem, sot.virk.Zenker, Farr, luutnantti Miettinen,etualalla oikealla Scott."), 'Ulkomaisten lehtimiesten retkikunta etulinjan komentopaikalla Tornion rintamalla 3/10-44. Komentaja, everstiluutnantti Halsti selostaa tilannetta kaistallaan piirtäen kepillä kartan maantiehen. Komentajasta oikealla: Björnsson Mehlem, sotilasvirkamies Zenker, sotilasvirkamies Farr, luutnantti Miettinen, etualalla oikealla Scott.')
        self.assertEqual(preprocessor("Viestiosasto 1: Sotilasradiosähköttäjien tutkinossa 27.4.1942 todistuksen saaneet, vas. oikealle: Vänrikki Aro, korpraali Räsänen, vänrikki Nordberg, sotilasmestari Kivi, luutnantti Päiviö, sotilasmestari Lavola, sot.virk. Halonen, alikersantti Rosenberg, vänrikki Lindblad, sot.virk. Österman, alikersantti Salenius."), 'Viestiosasto 1: Sotilasradiosähköttäjien tutkinossa 27.4.1942 todistuksen saaneet, vas. oikealle: vänrikki Aro, korpraali Räsänen, vänrikki Nordberg, sotilasmestari Kivi, luutnantti Päiviö, sotilasmestari Lavola, sotilasvirkamies Halonen, alikersantti Rosenberg, vänrikki Lindblad, sotilasvirkamies Österman, alikersantti Salenius.')
        self.assertEqual(preprocessor("Ev. luutn.Pasonen ja saks. Amiraali keskuselevat"), 'everstiluutnantti Pasonen ja saks. Amiraali keskuselevat')
        self.assertEqual(preprocessor("Ev. luutnantti Vänttinen"), 'everstiluutnantti Vänttinen')
        self.assertEqual(preprocessor("Ev. luutn. Rauramo"), 'everstiluutnantti Rauramo')
        self.assertEqual(preprocessor("TK-Pärttyli Virkki erään lennon jälkeen."), 'sotilasvirkamies Pärttyli Virkki erään lennon jälkeen.')
        self.assertEqual(preprocessor("Virkki,erään lennon jälkeen."), 'Virkki, erään lennon jälkeen.')
        self.assertEqual(preprocessor("TK-mies Hiisivaara."), 'sotilasvirkamies Hiisivaara.')
        self.assertEqual(preprocessor("Tk-miehet Varo, Itänen ja Tenkanen kuvaamassa Väinämöisen ammuntaa"),
                'sotilasvirkamies Varo, sotilasvirkamies Itänen sotilasvirkamies Tenkanen kuvaamassa Väinämöisen ammuntaa')
        self.assertEqual(preprocessor(
            "Rautaristin saajat: Eversti A. Puroma, majurit A.G. Airimo ja V. Lehvä, "
            "luutnantit K. Sarva ja U. Jalkanen, vänrikit T. Laakso, R. Kanto, N. Vuolle ja "
            "Y. Nuortio, kersantit T. Aspegren ja H. Kalliaisenaho, alikersantit L. Nousiainen, "
            "V. Launonen ja Salmi sekä korpraali R. Keihta."),
            'Rautaristin saajat: eversti A. Puroma, majuri A.G. Airimo majuri V. Lehvä, '
            'luutnantti K. Sarva luutnantti U. Jalkanen, vänrikki T. Laakso, vänrikki R. Kanto, '
            'vänrikki N. Vuolle vänrikki Y. Nuortio, kersantti T. Aspegren kersantti H. Kalliaisenaho, '
            'alikersantti L. Nousiainen, alikersantti V. Launonen alikersantti Salmi sekä '
            'korpraali R. Keihta.')

    def test_pruner(self):
        self.assertEqual(pruner('Kenraali Engelbrecht'), 'Kenraali Engelbrecht')
        self.assertEqual(pruner('Kenraali Engelbrecht retkellä'), None)
        self.assertEqual(pruner('höpö höpö Engelbrecht'), 'höpö höpö Engelbrecht')
        self.assertEqual(pruner('Höpö höpö Engelbrecht'), 'Höpö höpö Engelbrecht')
        self.assertEqual(pruner('Everstiluutnantti Berndt Eino Edvard Polón'), 'Everstiluutnantti Berndt Eino Edvard Polón')
        self.assertEqual(pruner('höpö höpö Engelbrecht:'), None)
        self.assertEqual(pruner('höpö höpö Engelbrecht '), None)
        self.assertEqual(pruner('kapteeni kissa'), None)
        self.assertEqual(pruner('höpö'), None)
        self.assertEqual(pruner('Engelbrecht'), None)
        self.assertEqual(pruner('#retkellä Engelbrecht'), None)
        self.assertEqual(pruner('K.-W.Grünn'), 'K.-W.Grünn')
        self.assertEqual(pruner('K.-W. Grünn'), 'K.-W. Grünn')

    def test_replace_sv_list(self):
        self.assertEqual(persons.replace_sv_list("TK-rintamakirjeenvaihtaja Yläjärvellä (vas. Sot.virk. Kapra, Jalkanen, vänr. Rahikainen)."), 'TK-rintamakirjeenvaihtaja Yläjärvellä (vas.  sotilasvirkamies Kapra, sotilasvirkamies Jalkanen,vänr. Rahikainen).')
        self.assertEqual(persons.replace_sv_list("Sotilasvirk. Kapra, Jalkanen, vänr. Rahikainen)."), ' sotilasvirkamies Kapra, sotilasvirkamies Jalkanen,vänr. Rahikainen).')
        self.assertEqual(persons.replace_sv_list("Sotilasvirkailija Kapra, Jalkanen, vänr. Rahikainen)."), ' sotilasvirkamies Kapra, sotilasvirkamies Jalkanen,vänr. Rahikainen).')
        self.assertEqual(persons.replace_sv_list("Komentajasta oikealla: Björnsson Mehlem, sot.virk.Zenker, Farr, luutnantti Miettinen,etualalla oikealla Scott."), 'Komentajasta oikealla: Björnsson Mehlem,  sotilasvirkamies Zenker, sotilasvirkamies Farr,luutnantti Miettinen,etualalla oikealla Scott.')

if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestPersonValidation))
    test_suite.addTest(doctest.DocTestSuite(persons))
    unittest.TextTestRunner().run(test_suite)
