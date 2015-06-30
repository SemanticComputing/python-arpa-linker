import argparse
import json
from urllib import parse, request
from urllib.error import HTTPError
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS
from rdflib.util import guess_format

class Arpa:
    """Class representing the ARPA service"""

    def __init__(self, url, min_ngram_length=1, ignore=None):
        """
        :param url: the ARPA service url
        :param min_ngram_length: the minimum ngram match length that will be included when
                                returning the query results
        :param ignore: a list of matches that should be removed from the results (case insensitive)
        """

        self.url = url
        self.ignore = [s.lower() for s in ignore or []]
        self.min_ngram_length = min_ngram_length

    def _filter(self, response):
        """
        Filter matches based on the ignore list and remove matches that are
        for ngrams with length less than self.min_ngram_length.

        :param response: the parsed ARPA service response
        :returns: the response with the ignored matches removed
        """

        # If the response is empty or there is nothing to ignore, do nothing
        if not (self.ignore or response['results']) and self.min_ngram_length == 1:
            return response

        # Filter ignored results
        res = [x for x in response['results'] if x['label'].lower() not in self.ignore]
        if self.min_ngram_length > 1:
            res = [x for x in res if len(x['properties']['ngram'][0].split()) >= self.min_ngram_length]

        response['results'] = res
        return response

    def query(self, text):
        """
        Query the ARPA service.

        :param text: the text used in the query 
        :returns: the ARPA service response as JSON
        """

        # Remove quotation marks and brackets - ARPA can return an error if they're present
        text = text.replace('"', '').replace("(", "").replace(")", "")
        data = parse.urlencode({ 'text': text }).encode('utf-8')
        # Query the ARPA service with the text
        req = request.Request(self.url, data)
        try:
            with request.urlopen(req) as response:
                read = json.loads(response.read().decode('utf-8'))
                return self._filter(read)
        except HTTPError as e:
            e.msg = 'Error ({}) when querying the ARPA service with data "{}".'.format(e.msg, data)
            raise

    def get_uri_matches(self, text):
        """
        Query ARPA and return matching uris.

        :param text: the text to use in the query
        :returns: a list of uris for resources that match the text
        """

        return [x['id'] for x in self.query(text)['results']]


def arpafy(graph, target_prop, arpa, source_prop=None, rdf_class=None):
    """
    Link a property to resources using ARPA. Modify the graph in place.

    :param graph: the graph to link (will be modified)
    :param target_prop: the property name that is used for saving the link
    :param arpa: the Arpa class instance
    :param source_prop: the property that's value will be used when querying ARPA (if omitted, skos:prefLabel is used)
    :param rdf_class: if given, only go through instances of this type.
    :returns: a dict with the amount of processed triples (processed), 
            match count (matches) and errors encountered (errors).
    """

    if source_prop is None:
        source_prop = SKOS['prefLabel']

    subgraph = Graph()

    if rdf_class:
        # Filter out subjects that are not of the given type
        for s in graph.subjects(RDF.type, rdf_class):
            subgraph += graph.triples((s, source_prop, None))
    else:
        subgraph += graph.triples((None, source_prop, None))

    match_count = 0
    errors = []

    for s, o in subgraph.subject_objects():
        try:
            match_uris = arpa.get_uri_matches(o)
        except HTTPError as e:
            errors.append(e)
        else:
            match_count += len(match_uris)
            # Add each uri found as a value of the target property
            for uri in match_uris:
                graph.add((s, target_prop, URIRef(uri)))

    return { 'processed': len(subgraph), 'matches': match_count, 'errors': errors }

def main():
    argparser = argparse.ArgumentParser(description="Link resources with ARPA.",
            fromfile_prefix_chars="@")
    argparser.add_argument("input", help="Input rdf file")
    argparser.add_argument("output", help="Output file")
    argparser.add_argument("tprop", help="Target property for the matches")
    argparser.add_argument("arpa", help="ARPA service URL")
    argparser.add_argument("--fi",
        help="Input file format (rdflib parser). Will be guessed if omitted.")
    argparser.add_argument("--fo",
        help="Output file format (rdflib serializer). Default is turtle.", default="turtle")
    argparser.add_argument("--rdfclass",
        help="Process only subjects of the given type (goes through all subjects by default).")
    argparser.add_argument("--prop",
        help="Property that's value is to be used in matching. Default is skos:prefLabel.")
    argparser.add_argument("--ignore", nargs="*",
        help="Terms that should be ignored even if matched")
    argparser.add_argument("--minngram", default=1, metavar="N", type=int,
        help="The minimum ngram length that is considered a match. Default is 1.")

    args = argparser.parse_args()

    if args.fi:
        input_format = args.fi
    else:
        input_format = guess_format(args.input)

    source_prop = None
    if args.prop:
        source_prop = URIRef(args.prop)

    rdf_class = None
    if args.rdfclass:
        rdf_class = URIRef(args.rdfclass)

    target_prop = URIRef(args.tprop)

    # Parse the input rdf file
    g = Graph()
    g.parse(args.input, format=input_format)

    arpa = Arpa(args.arpa, args.minngram, args.ignore)

    # Add the ARPA matches
    res = arpafy(g, target_prop, arpa, source_prop, rdf_class)

    if res['errors']:
        print("Some errors occurred while querying:")
        for err in res['errors']:
            print(err)

    print("Processed {} triples, found {} matches".format(res['processed'], res['matches']))

    # Serialize the graph to disk
    g.serialize(destination=args.output, format=args.fo)

if __name__ == '__main__':
    main()
