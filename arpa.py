import argparse
import json
from urllib import parse, request
from urllib.error import HTTPError
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS
from rdflib.util import guess_format

# The name of the property containing the label of the match in the ARPA results.
LABEL_PROP = 'label'
# The name of the property containing the type of the match in the ARPA results->properties
# Only needed for prioritized duplicate removal.
TYPE_PROP = 'type'

class Arpa:
    """Class representing the ARPA service"""

    def __init__(self, url, remove_duplicates=False, min_ngram_length=1, ignore=None):
        """
        :param url: The ARPA service url.
        :param remove_duplicates: If True, choose only one subject out of all the
                                matched subjects that have the same label (randomly).
                                If the value is a list or tuple, assume that it represents
                                a list of class names and prefer those classes when choosing
                                the subject. The ARPA results must include a property (TYPE_PROP)
                                that has the class of the match as the value.
        :param min_ngram_length: The minimum ngram match length that will be included when
                                returning the query results.
        :param ignore: A list of matches that should be removed from the results (case insensitive).
        """

        self.url = url
        self.ignore = [s.lower() for s in ignore or []]
        self.min_ngram_length = min_ngram_length
        if type(remove_duplicates) == bool:
            self.remove_duplicates = remove_duplicates
        else:
            self.remove_duplicates = tuple("<{}>".format(x) for x in remove_duplicates)

    def _remove_duplicates(self, entries):
        """
        Remove duplicates from the entries.
        A 'duplicate' is an entry with the same LABEL_PROP property value.
        If self.remove_duplicates == True, choose the subject to keep any which way.
        If self.remove_duplicates is a tuple (or a list), choose the kept subject
        by comparing its type to the types contained in the tuple. The lower the
        index of the type in the tuple, the higher the priority.

        :param entries: The ARPA service results as a JSON object.
        """

        res = entries
        if self.remove_duplicates == True:
            labels = set()
            add = labels.add
            res = [x for x in res if not (x[LABEL_PROP] in labels 
                # If the label is not in the labels set, add it to the set.
                # This works because set.add() returns None.
                or add(x[LABEL_PROP]))]

        elif self.remove_duplicates:
            # self.remove_duplicates is a tuple - prioritize types defined in it
            items = {}
            for x in res:
                # Get the types of the latest most preferrable entry that 
                # had the same label as this one
                prev_match_types = items.get(x[LABEL_PROP], {}).get('properties', {}).get(TYPE_PROP, [])
                # Get matches from the preferred types for the previously selected entry
                prev_pref = set(prev_match_types).intersection(set(self.remove_duplicates))
                try:
                    # Find the priority of the previously selected entry
                    prev_idx = min([self.remove_duplicates.index(t) for t in prev_pref])
                except ValueError:
                    # This is the first entry of its type
                    items[x[LABEL_PROP]] = x
                    continue
                # Get matches in the preferred types for this entry
                pref = set(x['properties'][TYPE_PROP]).intersection(self.remove_duplicates)
                try:
                    idx = min([self.remove_duplicates.index(t) for t in pref])
                except ValueError:
                    # This one is not of a preferred type
                    continue
                if idx < prev_idx:
                    # The current match has a higher priority preferred type -
                    # replace the entry selected earlier
                    items[x[LABEL_PROP]] = x

            res = [x for x in res if x in items.values()]

        return res

    def _filter(self, response):
        """
        Filter matches based on the ignore list and remove matches that are
        for ngrams with length less than self.min_ngram_length.

        :param response: The parsed ARPA service response.
        :returns: The response with the ignored matches removed.
        """

        res = response['results']

        # Filter ignored results
        if self.ignore:
            res = [x for x in res if x[LABEL_PROP].lower() not in self.ignore]

        # Filter by minimum ngram length
        if self.min_ngram_length > 1:
            res = [x for x in res if len(x['properties']['ngram'][0].split()) >= self.min_ngram_length]

        # Remove duplicates if requested
        res = self._remove_duplicates(res)

        response['results'] = res
        return response

    def query(self, text):
        """
        Query the ARPA service.

        :param text: The text used in the query.
        :returns: The ARPA service response as JSON.
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

        :param text: The text to use in the query.
        :returns: A list of uris for resources that match the text.
        """

        return [x['id'] for x in self.query(text)['results']]


def arpafy(graph, target_prop, arpa, source_prop=None, rdf_class=None):
    """
    Link a property to resources using ARPA. Modify the graph in place.

    :param graph: The graph to link (will be modified).
    :param target_prop: The property name that is used for saving the link.
    :param arpa: The Arpa class instance.
    :param source_prop: The property that's value will be used when querying ARPA (if omitted, skos:prefLabel is used).
    :param rdf_class: If given, only go through instances of this type.
    :returns: A dict with the amount of processed triples (processed), 
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
    argparser = argparse.ArgumentParser(description="Link resources to an RDF graph with ARPA.",
            fromfile_prefix_chars="@")
    argparser.add_argument("input", help="Input rdf file")
    argparser.add_argument("output", help="Output file")
    argparser.add_argument("tprop", metavar="target_property", help="Target property for the matches")
    argparser.add_argument("arpa", help="ARPA service URL")
    argparser.add_argument("--fi", metavar="INPUT_FORMAT",
        help="Input file format (rdflib parser). Will be guessed if omitted.")
    argparser.add_argument("--fo", metavar="OUTPUT_FORMAT",
        help="Output file format (rdflib serializer). Default is turtle.", default="turtle")
    argparser.add_argument("--rdf_class", metavar="CLASS",
        help="Process only subjects of the given type (goes through all subjects by default).")
    argparser.add_argument("--prop", metavar="PROPERTY",
        help="Property that's value is to be used in matching. Default is skos:prefLabel.")
    argparser.add_argument("--ignore", nargs="*", metavar="TERM",
        help="Terms that should be ignored even if matched")
    argparser.add_argument("--min_ngram", default=1, metavar="N", type=int,
        help="The minimum ngram length that is considered a match. Default is 1.")
    argparser.add_argument("--no_duplicates", nargs="*", default=False, metavar="TYPE",
        help="""Remove duplicate matches based on the 'label' returned by the ARPA service.
        Here 'duplicate' means an subject with the same label as another subject in
        the same result set.
        A list of types can be given with this argument. If given, prioritize matches
        based on it - the first given type will get the highest priority and so on.
        Note that the response from the service has to include a 'type' variable
        for this to work.""")

    args = argparser.parse_args()

    if args.fi:
        input_format = args.fi
    else:
        input_format = guess_format(args.input)

    source_prop = None
    if args.prop:
        source_prop = URIRef(args.prop)

    rdf_class = None
    if args.rdf_class:
        rdf_class = URIRef(args.rdf_class)

    target_prop = URIRef(args.tprop)
    if args.no_duplicates == []:
        no_duplicates = True
    else:
        no_duplicates = args.no_duplicates

    # Parse the input rdf file
    g = Graph()
    g.parse(args.input, format=input_format)

    arpa = Arpa(args.arpa, no_duplicates, args.min_ngram, args.ignore)

    # Query the ARPA service and add the matches
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
