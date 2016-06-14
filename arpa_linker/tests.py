import unittest
import responses
import logging
import re
from unittest import TestCase
from unittest.mock import patch, Mock
from requests.exceptions import HTTPError
from rdflib import Graph, Literal, URIRef
from arpa import Arpa, ArpaMimic, arpafy, process, parse_args, post, prune_candidates, \
    map_results, combine_candidates

candidate_response = {
    "locale": "fi",
    "results": {
        "Ha": [
            "Ha"
        ],
        "Hanko": [
            "Hanko"
        ],
        "hanko": [
            "hanko"
        ]
    }
}

sparql_result = {
    "head": {
        "vars": ["id", "ngram", "label", "etunimet", "sukunimi", "promotion_rank", "earliest_promotion_time", "death_date"]
    },
    "results": {
        "bindings": [
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Kenraaliluutnantti"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1917-04-25"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Kenraalimajuri"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1911-02-13"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Ratsuväenkenraali"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1918-03-07"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Sotamarsalkka"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1933-05-19"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Suomen Marsalkka"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1942-06-04"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Kenraaliluutnantti"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1917-04-25"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Kenraalimajuri"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1911-02-13"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Ratsuväenkenraali"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1918-03-07"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Sotamarsalkka"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1933-05-19"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Suomen Marsalkka"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1942-06-04"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_2"},
                "ngram": {"type": "literal", "value": "Joku Toinen"},
                "label": {"type": "literal", "value": "Joku Toinen"},
                "etunimet": {"type": "literal", "value": "Joku"},
                "sukunimi": {"type": "literal", "value": "TOINEN"},
                "promotion_rank": {"type": "literal", "value": "luutnantti"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1933-05-19"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1938-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_2"},
                "ngram": {"type": "literal", "value": "Joku Toinen"},
                "label": {"type": "literal", "value": "Joku Toinen"},
                "etunimet": {"type": "literal", "value": "Joku"},
                "sukunimi": {"type": "literal", "value": "TOINEN"},
                "promotion_rank": {"type": "literal", "value": "kapteeni"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1939-06-05"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1940-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_2"},
                "ngram": {"type": "literal", "value": "kapteeni Joku Toinen"},
                "label": {"type": "literal", "value": "Joku Toinen"},
                "etunimet": {"type": "literal", "value": "Joku"},
                "sukunimi": {"type": "literal", "value": "TOINEN"},
                "promotion_rank": {"type": "literal", "value": "kapteeni"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1939-06-05"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1940-01-27"}
            }
        ]
    }
}

sparql_result_with_duplicates = {
    "head": {
        "vars": ["id", "ngram", "label", "etunimet", "sukunimi", "promotion_rank", "earliest_promotion_time", "death_date"]
    },
    "results": {
        "bindings": [
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Suomen Marsalkka"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1942-06-04"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_2"},
                "ngram": {"type": "literal", "value": "Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "luutnantti"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1933-05-19"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1938-01-27"}
            }
        ]
    }
}

sparql_result_with_missing = {
    "head": {
        "vars": ["id", "ngram", "label", "etunimet", "sukunimi", "promotion_rank", "earliest_promotion_time", "death_date"]
    },
    "results": {
        "bindings": [
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Kenraaliluutnantti"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1917-04-25"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Kenraalimajuri"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1911-02-13"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Ratsuväenkenraali"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1918-03-07"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Sotamarsalkka"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1933-05-19"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Suomen Marsalkka"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1942-06-04"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Kenraaliluutnantti"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1917-04-25"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Kenraalimajuri"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1911-02-13"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Ratsuväenkenraali"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1918-03-07"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Sotamarsalkka"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1933-05-19"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_1"},
                "ngram": {"type": "literal", "value": "Carl Gustaf Mannerheim"},
                "label": {"type": "literal", "value": "Carl Gustaf Emil Mannerheim"},
                "etunimet": {"type": "literal", "value": "Carl Gustaf Emil"},
                "sukunimi": {"type": "literal", "value": "MANNERHEIM"},
                "promotion_rank": {"type": "literal", "value": "Suomen Marsalkka"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1942-06-04"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1951-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_2"},
                "ngram": {"type": "literal", "value": "Joku Toinen"},
                "label": {"type": "literal", "value": "Joku Toinen"},
                "etunimet": {"type": "literal", "value": "Joku"},
                "sukunimi": {"type": "literal", "value": "TOINEN"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1933-05-19"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1938-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_2"},
                "ngram": {"type": "literal", "value": "Joku Toinen"},
                "label": {"type": "literal", "value": "Joku Toinen"},
                "etunimet": {"type": "literal", "value": "Joku"},
                "sukunimi": {"type": "literal", "value": "TOINEN"},
                "promotion_rank": {"type": "literal", "value": "kapteeni"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1939-06-05"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1940-01-27"}
            },
            {
                "id": {"type": "uri", "value": "http://ldf.fi/warsa/actors/person_2"},
                "ngram": {"type": "literal", "value": "kapteeni Joku Toinen"},
                "label": {"type": "literal", "value": "Joku Toinen"},
                "etunimet": {"type": "literal", "value": "Joku"},
                "sukunimi": {"type": "literal", "value": "TOINEN"},
                "promotion_rank": {"type": "literal", "value": "kapteeni"},
                "earliest_promotion_time": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1939-06-05"},
                "death_date": {"datatype": "http://www.w3.org/2001/XMLSchema#date", "type": "typed-literal", "value": "1940-01-27"}
            }
        ]
    }
}

candidate_values = {Literal(x[0]) for x in candidate_response['results'].values()}

matches = {
    "locale": "fi",
    "results": [
        {
            "id": "http://ldf.fi/pnr/P_10311760",
            "label": "Hanko",
            "matches": [
                "Hanko"
            ],
            "properties": {
                "id": [
                    "<http://ldf.fi/pnr/P_10311760>"
                ],
                "label": [
                    "\"Hanko\"@fi"
                ],
                "ngram": [
                    "\"Hanko\""
                ],
                "type": [
                    "<http://ldf.fi/pnr-schema#place_type_540>"
                ]
            }
        },
        {
            "id": "http://ldf.fi/warsa/places/municipalities/m_place_506",
            "label": "Hanko",
            "matches": [
                "Hanko"
            ],
            "properties": {
                "id": [
                    "<http://ldf.fi/warsa/places/municipalities/m_place_506>"
                ],
                "label": [
                    "\"Hanko\"@fi"
                ],
                "ngram": [
                    "\"Hanko\""
                ],
                "type": [
                    "<http://www.yso.fi/onto/suo/kunta>"
                ]
            }
        },
        {
            "id": "http://ldf.fi/warsa/places/municipalities/m_place_504",
            "label": "Hanko Hanko",
            "matches": [
                "Hanko Hanko"
            ],
            "properties": {
                "id": [
                    "<http://ldf.fi/warsa/places/municipalities/m_place_504>"
                ],
                "label": [
                    "\"Hanko Hanko\"@fi"
                ],
                "ngram": [
                    "\"Hanko Hanko\""
                ],
                "type": [
                    "<http://www.yso.fi/onto/suo/kunta>"
                ]
            }
        }
    ]
}

match_uris = {URIRef(x['id']) for x in matches['results']}


def do_nothing(*args, **kwargs):
    pass


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


class TestArpa(TestCase):

    def setUp(self):
        self.candidate_response = candidate_response
        self.matches = matches

    @responses.activate
    def test_candidates_are_retrieved(self):
        responses.add(responses.POST, 'http://url?cgen',
                json=self.candidate_response, status=200,
                match_querystring=True)
        arpa = Arpa('http://url')
        res = arpa.get_candidates('Hanko')

        self.assertEqual(len(res), 3)
        for r in res:
            self.assertTrue(isinstance(r, Literal))

    @responses.activate
    def test_matches_are_retrieved(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)
        arpa = Arpa('http://url')
        res = arpa.get_uri_matches('Hanko')

        self.assertEqual(len(res), 3)
        for r in res:
            self.assertTrue(isinstance(r, URIRef))

    @responses.activate
    def test_arbitrary_duplicate_removal(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)
        arpa = Arpa('http://url', remove_duplicates=True)
        res = arpa.get_uri_matches('Hanko')

        self.assertEqual(len(res), 2)
        self.assertEqual(str(res[0]), 'http://ldf.fi/pnr/P_10311760')
        self.assertEqual(str(res[1]), 'http://ldf.fi/warsa/places/municipalities/m_place_504')

    @responses.activate
    def test_prioritized_duplicate_removal(self):
        no_dups = ['http://www.yso.fi/onto/suo/kunta']
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)
        arpa = Arpa('http://url', remove_duplicates=no_dups)
        res = arpa.get_uri_matches('Hanko Hanko')

        self.assertEqual(len(res), 2)
        self.assertEqual(str(res[0]), 'http://ldf.fi/warsa/places/municipalities/m_place_506')
        self.assertEqual(str(res[1]), 'http://ldf.fi/warsa/places/municipalities/m_place_504')

    @responses.activate
    def test_min_ngram_length(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)
        arpa = Arpa('http://url', min_ngram_length=2)
        res = arpa.get_uri_matches('Hanko Hanko')

        self.assertEqual(len(res), 1)
        self.assertEqual(str(res[0]), 'http://ldf.fi/warsa/places/municipalities/m_place_504')

    @responses.activate
    def test_ignore(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)
        arpa = Arpa('http://url', ignore=['Hanko Hanko'])
        res = arpa.get_uri_matches('Hanko Hanko')

        self.assertEqual(len(res), 2)
        self.assertEqual(str(res[0]), 'http://ldf.fi/pnr/P_10311760')
        self.assertEqual(str(res[1]), 'http://ldf.fi/warsa/places/municipalities/m_place_506')

    @responses.activate
    def test_retries(self):
        responses.add(responses.POST, 'http://url',
                body='error', status=503)

        arpa = Arpa('http://url', retries=1, wait_between_tries=0)

        self.assertRaises(HTTPError, arpa.get_uri_matches, 'Hanko Hanko')
        self.assertEqual(len(responses.calls), 2)

        responses.calls.reset()

        arpa = Arpa('http://url', wait_between_tries=0)

        self.assertRaises(HTTPError, arpa.get_uri_matches, 'Hanko Hanko')
        self.assertEqual(len(responses.calls), 1)

    def test_invalid_retries(self):
        self.assertRaises(ValueError, Arpa, 'url', retries=-1)
        self.assertRaises(TypeError, Arpa, 'url', retries=None)
        self.assertRaises(TypeError, Arpa, 'url', retries="string")

    def test_invalid_wait(self):
        self.assertRaises(ValueError, Arpa, 'url', wait_between_tries=-1)
        self.assertRaises(TypeError, Arpa, 'url', wait_between_tries=None)
        self.assertRaises(TypeError, Arpa, 'url', wait_between_tries="string")

    @responses.activate
    def test_all_params(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        arpa = Arpa('http://url', remove_duplicates=True, min_ngram_length=2,
                ignore=['Hanko'], retries=1, wait_between_tries=0)
        res = arpa.get_uri_matches('Hanko')

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0],
                URIRef('http://ldf.fi/warsa/places/municipalities/m_place_504'))

    @responses.activate
    def test_filter_all_out(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        arpa = Arpa('http://url', remove_duplicates=True,
                min_ngram_length=2, ignore=['Hanko Hanko'])
        res = arpa.get_uri_matches('Hanko')

        self.assertEqual(len(res), 0)

    @responses.activate
    def test_empty_response(self):
        responses.add(responses.POST, 'http://url', status=200)

        arpa = Arpa('http://url')

        self.assertRaises(HTTPError, arpa.get_uri_matches, 'Hanko')

    @responses.activate
    def test_empty_query(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        arpa = Arpa('http://url')

        self.assertRaises(ValueError, arpa.get_uri_matches, '')
        self.assertEqual(len(responses.calls), 0)


class TestArpaMimic(TestCase):
    def setUp(self):
        self.matches = sparql_result
        self.matches_with_dups = sparql_result_with_duplicates

    @responses.activate
    def test_matches_are_retrieved(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)
        arpa = ArpaMimic('', 'http://url')
        res = arpa.get_uri_matches('Hanko')

        self.assertEqual(len(res), 2)
        for r in res:
            self.assertTrue(isinstance(r, URIRef))

    @responses.activate
    def test_arbitrary_duplicate_removal(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches_with_dups, status=200)
        arpa = ArpaMimic('', 'http://url', remove_duplicates=True)
        res = arpa.get_uri_matches('Hanko')

        self.assertEqual(len(res), 1)

    @responses.activate
    def test_min_ngram_length(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches_with_dups, status=200)
        arpa = ArpaMimic('', 'http://url', min_ngram_length=2)
        res = arpa.get_uri_matches('Hanko Hanko')

        self.assertEqual(len(res), 1)
        self.assertEqual(str(res[0]), 'http://ldf.fi/warsa/actors/person_1')

    @responses.activate
    def test_ignore(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)
        arpa = ArpaMimic('', 'http://url', ignore=['Carl Gustaf Emil Mannerheim'])
        res = arpa.get_uri_matches('Hanko Hanko')

        self.assertEqual(len(res), 1)
        self.assertEqual(str(res[0]), 'http://ldf.fi/warsa/actors/person_2')

    @responses.activate
    def test_retries(self):
        responses.add(responses.POST, 'http://url',
                body='error', status=503)

        arpa = ArpaMimic('', 'http://url', retries=1, wait_between_tries=0)

        self.assertRaises(HTTPError, arpa.get_uri_matches, 'Hanko Hanko')
        self.assertEqual(len(responses.calls), 2)

        responses.calls.reset()

        arpa = Arpa('http://url', wait_between_tries=0)

        self.assertRaises(HTTPError, arpa.get_uri_matches, 'Hanko Hanko')
        self.assertEqual(len(responses.calls), 1)

    def test_invalid_retries(self):
        self.assertRaises(ValueError, ArpaMimic, '', 'url', retries=-1)
        self.assertRaises(TypeError, ArpaMimic, '', 'url', retries=None)
        self.assertRaises(TypeError, ArpaMimic, '', 'url', retries="string")

    def test_invalid_wait(self):
        self.assertRaises(ValueError, ArpaMimic, '', 'url', wait_between_tries=-1)
        self.assertRaises(TypeError, ArpaMimic, '', 'url', wait_between_tries=None)
        self.assertRaises(TypeError, ArpaMimic, '', 'url', wait_between_tries="string")

    @responses.activate
    def test_all_params(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        arpa = ArpaMimic('', 'http://url', remove_duplicates=True,
                min_ngram_length=2, ignore=['Joku Toinen'], retries=1)
        res = arpa.get_uri_matches('Hanko')

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(len(res), 1)
        self.assertEqual(str(res[0]), 'http://ldf.fi/warsa/actors/person_1')

    @responses.activate
    def test_filter_all_out(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        arpa = ArpaMimic('', 'http://url', remove_duplicates=True,
                min_ngram_length=2, ignore=['Carl Gustaf Emil Mannerheim', 'Joku Toinen'])
        res = arpa.get_uri_matches('Hanko')

        self.assertEqual(len(res), 0)

    @responses.activate
    def test_empty_response(self):
        responses.add(responses.POST, 'http://url', status=200)

        arpa = ArpaMimic('', 'http://url')

        self.assertRaises(HTTPError, arpa.get_uri_matches, 'Hanko')

    @responses.activate
    def test_empty_query(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        arpa = ArpaMimic('', 'http://url')

        self.assertRaises(ValueError, arpa.get_uri_matches, '')
        self.assertEqual(len(responses.calls), 0)


class TestArpafy(TestCase):
    def setUp(self):
        self.matches = matches
        self.candidate_response = candidate_response

        self.prop = URIRef('http://warsa/place')
        self.tprop = URIRef('http://warsa/target')
        self.triple = (URIRef('http://warsa/event'), self.prop, Literal('Hanko'))
        self.graph = Graph()
        self.graph.add(self.triple)

    @responses.activate
    def test_candidates_only(self):
        responses.add(responses.POST, 'http://url',
                json=self.candidate_response, status=200)

        output_graph = Graph()
        arpa = Arpa('http://url')
        res = arpafy(self.graph, self.tprop, arpa,
                source_prop=self.prop,
                output_graph=output_graph,
                candidates_only=True)

        self.assertEqual(res['graph'], output_graph)
        self.assertEqual(res['matches'], 3)
        self.assertEqual(len(output_graph), 3)
        self.assertEqual(len(set(output_graph.subjects())), 1)
        self.assertEqual(set(output_graph.objects()), candidate_values)

    @responses.activate
    def test_matches_in_new_graph(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        output_graph = Graph()
        arpa = Arpa('http://url')
        res = arpafy(self.graph, self.tprop, arpa,
                source_prop=self.prop,
                output_graph=output_graph)

        self.assertEqual(res['graph'], output_graph)
        self.assertEqual(res['matches'], 3)
        self.assertEqual(len(output_graph), 3)
        self.assertEqual(len(set(output_graph.subjects())), 1)
        self.assertEqual(set(output_graph.objects()), match_uris)

    @responses.activate
    def test_matches_in_same_graph(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        original_len = len(self.graph)

        arpa = Arpa('http://url')
        res = arpafy(self.graph, self.tprop, arpa,
                source_prop=self.prop,
                output_graph=self.graph)

        self.assertEqual(res['graph'], self.graph)
        self.assertEqual(res['matches'], 3)
        self.assertEqual(len(self.graph), original_len + 3)
        self.assertEqual(set(self.graph.objects(predicate=self.tprop)), match_uris)

    @responses.activate
    def test_validation(self):

        class Validator:
            def __init__(self, *args):
                pass

            def validate(self, results, text, *args, **kwargs):
                res = []
                for r in results:
                    if r['label'] != 'Hanko':
                        res.append(r)
                return res

        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        output_graph = Graph()
        arpa = Arpa('http://url')
        res = arpafy(self.graph, self.tprop, arpa,
                source_prop=self.prop,
                output_graph=output_graph, validator_class=Validator)

        self.assertEqual(res['graph'], output_graph)

        self.assertEqual(res['matches'], 1)
        self.assertEqual(len(output_graph), 1)
        self.assertEqual(len(set(output_graph.subjects())), 1)

    @responses.activate
    def test_preprocessor(self):
        replaced = 'other'

        def preprocessor(text, *args):
            return replaced

        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        arpa = Arpa('http://url')
        arpafy(self.graph, self.tprop, arpa,
                source_prop=self.prop,
                preprocessor=preprocessor)

        self.assertEqual(len(responses.calls), 1, responses.calls[0].request.body)
        self.assertEqual(responses.calls[0].request.body, 'text=' + replaced)


class TestProcess(TestCase):
    def setUp(self):
        self.matches = matches
        self.candidate_response = candidate_response
        self.sparql_result = sparql_result

        Graph.parse = do_nothing
        Graph.serialize = do_nothing

        self.prop = URIRef('http://warsa/place')
        self.tprop = URIRef('http://warsa/target')
        self.triple = (URIRef('http://warsa/event'), self.prop, Literal('Hanko'))
        self.graph = Graph()
        self.graph.add(self.triple)

        self.first_side_effect = True

        def get_side_effect():
            if not self.first_side_effect:
                return Graph()
            self.first_side_effect = False
            return self.graph

        self.get_side_effect = get_side_effect

    @responses.activate
    @patch('arpa.Graph')
    def test_process_in_same_graph(self, mocked_graph):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        mocked_graph.side_effect = [self.graph, Graph()]

        arpa = Arpa('http://url')
        original_len = len(self.graph)

        res = process('input', 'turtle', 'output', 'turtle', source_prop=self.prop,
                target_prop=self.tprop, arpa=arpa)

        self.assertEqual(len(res['graph']), original_len + len(match_uris))

    @responses.activate
    @patch('arpa.Graph')
    def test_process_in_new_graph(self, mocked_graph):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        mocked_graph.side_effect = self.get_side_effect
        arpa = Arpa('http://url')

        res = process('input', 'turtle', 'output', 'turtle', source_prop=self.prop,
                target_prop=self.tprop, arpa=arpa, new_graph=True)

        self.assertEqual(len(set(res['graph'].objects())), len(match_uris))
        self.assertEqual(set(res['graph'].objects()), set(match_uris))
        self.assertEqual(res['processed'], 1)
        self.assertEqual(res['matches'], 3)
        self.assertEqual(res['subjects_matched'], 1)
        self.assertEqual(res['errors'], [])

    @responses.activate
    @patch('arpa.Graph')
    def test_combine_candidates(self, mocked_graph):
        responses.add(responses.POST, 'http://url',
                json=self.sparql_result, status=200)

        mocked_graph.side_effect = self.get_side_effect

        subject_uri = URIRef('http://warsa/event')
        self.value = 'Hanko'
        self.value2 = 'Toinen'
        self.prop = URIRef('http://warsa/place')
        self.triple = (subject_uri, self.prop, Literal(self.value))
        self.triple2 = (subject_uri, self.prop, Literal(self.value2))
        self.graph = Graph()
        self.graph.add(self.triple)
        self.graph.add(self.triple2)

        res = process('input', 'turtle', 'output', 'turtle', source_prop=self.prop,
                target_prop=self.tprop, arpa=ArpaMimic('', 'http://url'),
                join_candidates=True)

        g = res['graph']

        self.assertEqual(3, len(g))
        val = str(list(g.objects(predicate=self.prop))[0])
        self.assertTrue('Hanko' in val)
        self.assertTrue('Toinen' in val)
        self.assertTrue(re.match('"\w+" "\w+"', val))

    @patch('arpa.Graph')
    def test_prune_only_same_graph(self, mocked_graph):
        def nop_pruner(cand):
            return cand

        mocked_graph.side_effect = [self.graph, Graph()]

        original_len = len(self.graph)

        res = process('input', 'turtle', 'output', 'turtle', source_prop=self.prop,
                target_prop=self.tprop, prune=True, pruner=nop_pruner, run_arpafy=False)

        self.assertEqual(res['graph'], self.graph)
        self.assertEqual(len(self.graph), original_len)

    @patch('arpa.Graph')
    def test_prune_only_new_graph(self, mocked_graph):
        def no_res_pruner(cand):
            return None

        mocked_graph.side_effect = [self.graph, Graph(), Graph()]

        original_len = len(self.graph)

        res = process('input', 'turtle', 'output', 'turtle', source_prop=self.prop,
                target_prop=self.tprop, new_graph=True, prune=True,
                pruner=no_res_pruner, run_arpafy=False)

        self.assertNotEqual(res['graph'], self.graph)
        self.assertEqual(original_len, len(self.graph))
        self.assertEqual(0, len(res['graph']))


class TestParseArgs(TestCase):
    def setUp(self):
        self.base_params = ['input.ttl', 'output.ttl', 'target', 'url']

    def test_parse_empty_args(self):
        self.assertRaises(SystemExit, parse_args, [])

    def test_parse_minimal_args(self):
        args = parse_args(self.base_params)

        self.assertEqual(args.input, 'input.ttl')
        self.assertEqual(args.output, 'output.ttl')
        self.assertEqual(args.tprop, URIRef('target'))
        self.assertEqual(args.arpa, 'url')

        self.assertEqual(args.fi, 'turtle')
        self.assertEqual(args.fo, 'turtle')
        self.assertEqual(args.min_ngram, 1)
        self.assertEqual(args.no_duplicates, False)
        self.assertEqual(args.new_graph, False)
        self.assertEqual(args.retries, 0)
        self.assertEqual(args.wait, 1)
        self.assertEqual(args.log_level, 'INFO')

        self.assertEqual(args.prop, None)
        self.assertEqual(args.rdf_class, None)
        self.assertEqual(args.ignore, None)

    def test_rdf_class(self):
        params = self.base_params + ['--rdf_class', 'http://type']
        params = ['input.ttl', 'output.ttl', 'target', 'url', '--rdf_class', 'http://type']
        args = parse_args(params)

        self.assertEqual(args.rdf_class, URIRef('http://type'))

    def test_prop(self):
        params = self.base_params + ['--prop', 'property']
        args = parse_args(params)

        self.assertEqual(args.prop, URIRef('property'))

    def test_new_graph(self):
        params = self.base_params + ['--new_graph']
        args = parse_args(params)

        self.assertEqual(args.new_graph, True)

        params = self.base_params + ['-n']
        args = parse_args(params)

        self.assertEqual(args.new_graph, True)

    def test_candidates_only(self):
        params = self.base_params + ['--candidates_only']
        args = parse_args(params)

        self.assertEqual(args.candidates_only, True)

        params = self.base_params + ['-c']
        args = parse_args(params)

        self.assertEqual(args.candidates_only, True)

    def test_min_ngram(self):
        params = self.base_params + ['--min_ngram', '2']
        args = parse_args(params)

        self.assertEqual(args.min_ngram, 2)

    def test_ignore(self):
        params = self.base_params + ['--ignore', 'foo', 'bar']
        args = parse_args(params)

        self.assertEqual(args.ignore, ['foo', 'bar'])

    def test_no_duplicates(self):
        params = self.base_params + ['--no_duplicates']
        args = parse_args(params)

        self.assertEqual(args.no_duplicates, True)

        params = self.base_params + ['--no_duplicates', 'foo', 'bar']
        args = parse_args(params)

        self.assertEqual(args.no_duplicates, ['foo', 'bar'])

    def test_retries(self):
        params = self.base_params + ['--retries', '2']
        args = parse_args(params)

        self.assertEqual(args.retries, 2)

        params = self.base_params + ['-r', '3']
        args = parse_args(params)

        self.assertEqual(args.retries, 3)

    def test_wait(self):
        params = self.base_params + ['--retries', '2']
        params_long = params + ['--wait', '3']
        args = parse_args(params_long)

        self.assertEqual(args.wait, 3)

        params_short = params + ['-w', '4']
        args = parse_args(params_short)

        self.assertEqual(args.wait, 4)

    def test_log_level(self):
        params = self.base_params + ['--log_level', 'DEBUG']
        args = parse_args(params)

        self.assertEqual(args.log_level, 'DEBUG')

        params = self.base_params + ['--log_level', 'WRONG']
        self.assertRaises(SystemExit, parse_args, params)


class TestPruneCandidates(TestCase):
    def setUp(self):
        self.value = 'Hanko'
        self.value2 = 'Toinen'
        self.prop = URIRef('http://warsa/place')
        self.tprop = URIRef('http://warsa/target')
        self.triple = (URIRef('http://warsa/event'), self.prop, Literal(self.value))
        self.triple2 = (URIRef('http://warsa/event'), self.prop, Literal(self.value2))
        self.graph = Graph()
        self.graph.add(self.triple)
        self.graph.add(self.triple2)

    def test_nop_pruner(self):
        def pruner(cand):
            return cand

        g = prune_candidates(self.graph, self.prop, pruner)['graph']

        self.assertEqual(self.graph, g)

        self.assertEqual(2, len(g))
        self.assertTrue(self.triple in g)
        self.assertTrue(self.triple2 in g)

    def test_no_results(self):
        def pruner(cand):
            return None

        g = prune_candidates(self.graph, self.prop, pruner)['graph']

        self.assertEqual(self.graph, g)

        self.assertEqual(0, len(g))

    def test_prune_some(self):
        def pruner(cand):
            return cand if cand == 'Hanko' else None

        g = prune_candidates(self.graph, self.prop, pruner)['graph']

        self.assertEqual(self.graph, g)

        self.assertEqual(1, len(g))
        self.assertEqual(self.value, str(list(g.objects())[0]))

    def test_output_graph(self):
        def pruner(cand):
            return cand if cand == 'Hanko' else None

        g = Graph()
        res_g = prune_candidates(self.graph, self.prop, pruner, output_graph=g)['graph']

        self.assertEqual(g, res_g)

        self.assertEqual(1, len(g))
        self.assertEqual(self.value, str(list(g.objects())[0]))

        self.assertEqual(2, len(self.graph))
        self.assertTrue(self.triple in self.graph)
        self.assertTrue(self.triple2 in self.graph)


class TestPost(TestCase):
    def setUp(self):
        self.matches = matches
        self.data = {'text': 'text'}
        self.empty_response = {}
        self.url = 'http://url'
        self.error = {'error': 'error'}

    @responses.activate
    def test_post(self):
        responses.add(responses.POST, self.url,
                json=self.matches, status=200)

        res = post(self.url, {'text': 'Hanko'})
        self.assertEqual(res, self.matches)

    @responses.activate
    def test_no_data(self):
        responses.add(responses.POST, self.url,
                json=self.empty_response, status=200)

        self.assertRaises(HTTPError, post, url=self.url, data=None)

    @responses.activate
    def test_empty_response(self):
        responses.add(responses.POST, self.url, status=200)

        self.assertRaises(HTTPError, post, url=self.url, data=self.data)

    @responses.activate
    def test_retries(self):
        responses.add(responses.POST, 'http://url',
                json=self.error, status=503)

        self.assertRaises(HTTPError, post, url=self.url, data=self.data, retries=1, wait=0)
        self.assertEqual(len(responses.calls), 2)

        responses.calls.reset()

        self.assertRaises(HTTPError, post, url=self.url, data=self.data, retries=10, wait=0)
        self.assertEqual(len(responses.calls), 11)

        responses.calls.reset()

        self.assertRaises(HTTPError, post, url=self.url, data=self.data, retries=0, wait=0)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    @patch('arpa.time')
    def test_wait(self, mock_time):
        responses.add(responses.POST, 'http://url',
                json=self.error, status=503)

        mock_time.sleep = Mock(return_value=None)

        wait = 10

        self.assertRaises(HTTPError, post, url=self.url, data=self.data, retries=0, wait=wait)
        self.assertEqual(len(responses.calls), 1)
        mock_time.sleep.assert_not_called()

        responses.calls.reset()

        self.assertRaises(HTTPError, post, url=self.url, data=self.data, retries=1,
                wait=wait)
        mock_time.sleep.assert_called_once_with(wait)

        responses.calls.reset()
        mock_time.sleep.reset_mock()

        self.assertRaises(HTTPError, post, url=self.url, data=self.data, retries=0)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_invalid_retries(self):
        responses.add(responses.POST, self.url,
                json=self.matches, status=200)

        self.assertRaises(ValueError, post, url=self.url, data=self.data,
                retries=-1)

        self.assertRaises(TypeError, post, url=self.url, data=self.data,
                retries=None)

        self.assertRaises(TypeError, post, url=self.url, data=self.data,
                retries="string")

    @responses.activate
    def test_invalid_wait(self):
        responses.add(responses.POST, self.url,
                json=self.matches, status=200)

        self.assertRaises(ValueError, post, url=self.url, data=self.data,
                wait=-1)

        self.assertRaises(TypeError, post, url=self.url, data=self.data,
                wait=None)

        self.assertRaises(TypeError, post, url=self.url, data=self.data,
                wait="string")


class TestMapResults(TestCase):
    def setUp(self):
        self.ranks = ['"Kenraaliluutnantti"', '"Kenraalimajuri"', '"Ratsuväenkenraali"',
                '"Sotamarsalkka"', '"Suomen Marsalkka"', '"Kenraaliluutnantti"',
                '"Kenraalimajuri"', '"Ratsuväenkenraali"', '"Sotamarsalkka"',
                '"Suomen Marsalkka"']
        self.ranks2 = ['"luutnantti"', '"kapteeni"', '"kapteeni"']
        self.ranks_missing = ['"kapteeni"', '"kapteeni"']
        self.ngrams = ['Gustaf Mannerheim', 'Carl Gustaf Mannerheim']
        self.ngrams2 = ['Joku Toinen', 'kapteeni Joku Toinen']
        self.sparql_result = sparql_result
        self.sparql_result_with_missing = sparql_result_with_missing

    def test_map(self):
        res = map_results(self.sparql_result)['results']
        self.assertEqual(2, len(res))
        self.assertEqual(res[0]['properties']['promotion_rank'], self.ranks)
        self.assertEqual(res[0]['matches'], self.ngrams)
        self.assertEqual(res[1]['properties']['promotion_rank'], self.ranks2)
        self.assertEqual(res[1]['matches'], self.ngrams2)

    def test_map_with_missing_values(self):
        res = map_results(self.sparql_result_with_missing)['results']
        self.assertEqual(2, len(res))
        self.assertEqual(res[0]['properties']['promotion_rank'], self.ranks)
        self.assertEqual(res[0]['matches'], self.ngrams)
        self.assertEqual(res[1]['properties']['promotion_rank'], self.ranks_missing)
        self.assertEqual(res[1]['matches'], self.ngrams2)


class TestCombineCandidates(TestCase):
    def setUp(self):
        self.value = 'Hanko'
        self.value2 = 'Toinen'
        self.prop = URIRef('http://warsa/place')
        self.triple = (URIRef('http://warsa/event'), self.prop, Literal(self.value))
        self.triple2 = (URIRef('http://warsa/event'), self.prop, Literal(self.value2))
        self.graph = Graph()
        self.graph.add(self.triple)
        self.graph.add(self.triple2)

    def test_combine(self):
        g = combine_candidates(self.graph, self.prop)

        self.assertEqual(self.graph, g)

        self.assertEqual(1, len(g))
        val = str(list(g.objects())[0])
        self.assertTrue('Hanko' in val)
        self.assertTrue('Toinen' in val)
        self.assertTrue(re.match('"\w+" "\w+"', val))

if __name__ == '__main__':
    unittest.main()
