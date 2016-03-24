import unittest
import responses
from unittest import TestCase
from unittest.mock import Mock, patch
from requests.exceptions import HTTPError
from arpa_linker.arpa import Arpa, arpafy, process
from rdflib import Graph, Literal, URIRef

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

        arpa = Arpa('http://url', retries=1)
        self.assertRaises(HTTPError, arpa.get_uri_matches, 'Hanko Hanko')
        self.assertEqual(len(responses.calls), 2)

        responses.calls.reset()

        arpa = Arpa('http://url')
        self.assertRaises(HTTPError, arpa.get_uri_matches, 'Hanko Hanko')
        self.assertEqual(len(responses.calls), 1)

    def test_negative_retries(self):
        self.assertRaises(ValueError, Arpa, 'url', retries=-1)

    @responses.activate
    def test_all_params(self):
        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        arpa = Arpa('http://url', remove_duplicates=True,
                min_ngram_length=2, ignore=['Hanko'], retries=1)
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

        def validator(graph, s):
            self.assertEqual(graph, self.graph)

            def validate(text, results):
                res = []
                for r in results:
                    if r['label'] != 'Hanko':
                        res.append(r)
                return res

            return validate

        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        output_graph = Graph()
        arpa = Arpa('http://url')
        res = arpafy(self.graph, self.tprop, arpa,
                source_prop=self.prop,
                output_graph=output_graph,
                validator=validator)

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

        Graph.parse = do_nothing
        Graph.serialize = do_nothing

        self.prop = URIRef('http://warsa/place')
        self.tprop = URIRef('http://warsa/target')
        self.triple = (URIRef('http://warsa/event'), self.prop, Literal('Hanko'))
        self.graph = Graph()
        self.graph.add(self.triple)

    @responses.activate
    @patch('arpa_linker.arpa.Graph')
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
    @patch('arpa_linker.arpa.Graph')
    def test_process_in_new_graph(self, mocked_graph):
        self.first_side_effect = True

        def get_side_effect():
            if not self.first_side_effect:
                return Graph()
            self.first_side_effect = False
            return self.graph

        responses.add(responses.POST, 'http://url',
                json=self.matches, status=200)

        mocked_graph.side_effect = get_side_effect
        arpa = Arpa('http://url')

        res = process('input', 'turtle', 'output', 'turtle', source_prop=self.prop,
                target_prop=self.tprop, arpa=arpa, new_graph=True)

        self.assertEqual(len(set(res['graph'].objects())), len(match_uris))
        self.assertEqual(set(res['graph'].objects()), set(match_uris))
        self.assertEqual(res['processed'], 1)
        self.assertEqual(res['matches'], 3)
        self.assertEqual(res['subjects_matched'], 1)
        self.assertEqual(res['errors'], [])

if __name__ == '__main__':
    unittest.main()
