"""
A module for linking resources to an RDF graph with an [ARPA](https://github.com/jiemakel/arpa) service.

## Requirements
Python 3, [RDFLib](http://rdflib.readthedocs.org/en/latest/) and [Requests](http://docs.python-requests.org/en/latest/)

If you want to see a progress bar, you'll need [PyPrind](https://github.com/rasbt/pyprind).

## Usage

The module can be invoked as a script from the command line or by calling `arpa.arpafy` (or `arpa.process`) in your Python code.

    usage: arpa.py [-h] [--fi INPUT_FORMAT] [--fo OUTPUT_FORMAT]
                [--rdf_class CLASS] [--prop PROPERTY]
                [--ignore [TERM [TERM ...]]] [--min_ngram N]
                [--no_duplicates [TYPE [TYPE ...]]]
                input output target_property arpa

    Link resources to an RDF graph with ARPA.

    positional arguments:
    input                 Input rdf file
    output                Output file
    target_property       Target property for the matches
    arpa                  ARPA service URL

    optional arguments:
    -h, --help            show this help message and exit
    --fi INPUT_FORMAT     Input file format (rdflib parser). Will be guessed if
                          omitted.
    --fo OUTPUT_FORMAT    Output file format (rdflib serializer). Default is
                          turtle.
    --rdf_class CLASS     Process only subjects of the given type (goes through
                          all subjects by default).
    --prop PROPERTY       Property that's value is to be used in matching.
                          Default is skos:prefLabel.
    --ignore [TERM [TERM ...]]
                        Terms that should be ignored even if matched
    --min_ngram N         The minimum ngram length that is considered a match.
                          Default is 1.
    --no_duplicates [TYPE [TYPE ...]]
                        Remove duplicate matches based on the 'label' returned
                        by the ARPA service. Here 'duplicate' means a subject
                        with the same label as another subject in the same
                        result set. A list of types can be given with this
                        argument. If given, prioritize matches based on it -
                        the first given type will get the highest priority and
                        so on. Note that the response from the service has to
                        include a 'type' variable for this to work.

The arguments can also be read from a file using "@" (example arg file [arpa.args](https://github.com/SemanticComputing/python-arpa-linker/blob/master/arpa.args)):

`$ python3 arpa.py @arpa.args`

## Examples

See [menehtyneet.py](https://github.com/SemanticComputing/python-arpa-linker/blob/master/menehtyneet.py) and
[places.py](https://github.com/SemanticComputing/python-arpa-linker/blob/master/places.py) for code examples
and [arpa.args](https://github.com/SemanticComputing/python-arpa-linker/blob/master/arpa.args) for an example arg file.
"""

import argparse
import requests
import time
from datetime import timedelta
from requests.exceptions import HTTPError
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS
from rdflib.util import guess_format

__all__ = ['Arpa', 'arpafy', 'process', 'main', 'LABEL_PROP', 'TYPE_PROP']

LABEL_PROP = 'label'
"""The name of the property containing the label of the match in the ARPA results."""

TYPE_PROP = 'type'
"""
The name of the property containing the type of the match in the ARPA results->properties.
Only needed for prioritized duplicate removal.
"""

class Arpa:
    """Class representing the ARPA service"""

    def __init__(self, url, remove_duplicates=False, min_ngram_length=1, ignore=None):
        """
        Initialize the Arpa service object.

        `url` is the ARPA service url.

        If `remove_duplicates` is `True`, choose only one subject out of all the
        matched subjects that have the same label (arbitrarily).
        If, instead, the value is a list or a tuple, assume that it represents
        a list of class names and prefer those classes when choosing
        the subject. The ARPA results must include a property (`TYPE_PROP`)
        that has the class of the match as the value.

        `min_ngram_length` is the minimum ngram match length that will be included when
        returning the query results.

        `ignore` is a list of matches that should be removed from the results (case insensitive).
        """

        self._url = url
        self._ignore = [s.lower() for s in ignore or []]
        self._min_ngram_length = min_ngram_length

        if type(remove_duplicates) == bool:
            self._no_duplicates = remove_duplicates
        else:
            self._no_duplicates = tuple("<{}>".format(x) for x in remove_duplicates)

    def _remove_duplicates(self, entries):
        """
        Remove duplicates from the entries.

        A 'duplicate' is an entry with the same `LABEL_PROP` property value.
        If `self._no_duplicates == True`, choose the subject to keep any which way.
        If `self._no_duplicates` is a tuple (or a list), choose the kept subject
        by comparing its type to the types contained in the tuple. The lower the
        index of the type in the tuple, the higher the priority.

        `entries` is the ARPA service results as a JSON object.
        """

        res = entries
        if self._no_duplicates == True:
            labels = set()
            add = labels.add
            res = [x for x in res if not (x[LABEL_PROP] in labels 
                # If the label is not in the labels set, add it to the set.
                # This works because set.add() returns None.
                or add(x[LABEL_PROP]))]

        elif self._no_duplicates:
            # self._no_duplicates is a tuple - prioritize types defined in it
            items = {}
            for x in res:
                x_label = x[LABEL_PROP].lower()
                # Get the types of the latest most preferrable entry that 
                # had the same label as this one
                prev_match_types = items.get(x_label, {}).get('properties', {}).get(TYPE_PROP, [])
                # Get matches from the preferred types for the previously selected entry
                prev_pref = set(prev_match_types).intersection(set(self._no_duplicates))
                try:
                    # Find the priority of the previously selected entry
                    prev_idx = min([self._no_duplicates.index(t) for t in prev_pref])
                except ValueError:
                    # No previous entry or previous entry doesn't have a preferred type
                    prev_idx = float('inf')
                # Get matches in the preferred types for this entry
                pref = set(x['properties'][TYPE_PROP]).intersection(self._no_duplicates)
                try:
                    idx = min([self._no_duplicates.index(t) for t in pref])
                except ValueError:
                    # This one is not of a preferred type
                    idx = float('inf')

                if (not prev_match_types) or idx < prev_idx:
                    # There is no previous entry with this label or
                    # the current match has a higher priority preferred type
                    items[x_label] = x

            res = [x for x in res if x in items.values()]

        return res

    def _filter(self, response):
        """
        Filter matches based on `self._ignore` and remove matches that are
        for ngrams with length less than `self.min_ngram_length`.

        Return the response with the ignored matches removed.

        `response` is the parsed ARPA service response.
        """

        res = response['results']

        # Filter ignored results
        if self._ignore:
            res = [x for x in res if x[LABEL_PROP].lower() not in self._ignore]

        # Filter by minimum ngram length
        if self._min_ngram_length > 1:
            res = [x for x in res if len(x['properties']['ngram'][0].split()) >= self._min_ngram_length]

        # Remove duplicates if requested
        res = self._remove_duplicates(res)

        response['results'] = res
        return response

    def _sanitize(self, text):
        # Remove quotation marks and brackets - ARPA can return an error if they're present
        return text.replace('"', '').replace("(", "").replace(")", "")

    def query(self, text):
        """
        Query the ARPA service and return the response as JSON

        `text` is the text used in the query.
        """

        text = self._sanitize(text)
        # Query the ARPA service with the text
        data = 'text="{}"'.format(text)
        res = requests.post(self._url, data={'text': text})
        try:
            res.raise_for_status()
        except HTTPError as e:
            raise HTTPError('Error ({}) when querying the ARPA service with data "{}".'.format(e.response.status_code, data))

        return self._filter(res.json())

    def get_uri_matches(self, text, validator=None):
        """
        Query ARPA and return a list of uris for resources that match the text.

        `text` is the text to use in the query.

        `validator` is a function that takes the ARPA results as parameter and returns
        validated results.
        """

        results = self.query(text)['results']

        if validator:
            results = validator(results)

        return [x['id'] for x in results]

class Bar:
    """
    Mock progress bar implementation
    """
    def __init__(self, n):
        self.n = n
    def update(self):
        pass

def get_bar(n, use_pyprind):
    """
    Get a progress bar.
    `n` is the number of iterations for the progress bar.
    If `use_pyprind` is true, try to return a pyprind.ProgBar instance. Otherwise,
    return a mock progress bar.
    """

    if use_pyprind:
        try:
            import pyprind
            return pyprind.ProgBar(n)
        except ImportError:
            pass

    return Bar(n)


def arpafy(graph, target_prop, arpa, source_prop=None, rdf_class=None,
            preprocessor=None, validator=None, progress=None):
    """
    Link a property to resources using ARPA. Modify the graph in place.

    Return a dict with the amount of processed triples (processed), 
    match count (matches) and errors encountered (errors).

    `graph` is the graph to link (will be modified).

    `target_prop` is the property name that is used for saving the link.

    `arpa` is the Arpa class instance.

    `source_prop` is the property that's value will be used when querying ARPA (if omitted, skos:prefLabel is used).

    If `rdf_class` is given, only go through instances of this type.

    `preprocessor` is an optional function that processes the query text before it is used in the ARPA query.

    `validator` is a function that takes a graph and a subject as parameter and returns a function
    that takes the original graph and the ARPA results as parameter and returns a subset of those results
    (that have been validated based on the subject, graph and results). Optional.
    This is a function and not an object because of reasons.

    If `progress` is `True`, show a progress bar. Requires pyprind.
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
    
    bar = get_bar(len(subgraph), progress)

    for s, o in subgraph.subject_objects():
        o = preprocessor(o) if preprocessor else o
        args = (o, validator(graph, s)) if validator else (o,)
        try:
            match_uris = arpa.get_uri_matches(*args)
        except (HTTPError, ValueError) as e:
            errors.append(e)
        else:
            match_count += len(match_uris)
            # Add each uri found as a value of the target property
            for uri in match_uris:
                graph.add((s, target_prop, URIRef(uri)))
        bar.update()

    return { 'processed': len(subgraph), 'matches': match_count, 'errors': errors }

def main():
    """Main function for running via the command line."""

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
        Here 'duplicate' means a subject with the same label as another subject in
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
    process(g, target_prop, arpa, source_prop, rdf_class, progress=True)

    # Serialize the graph to disk
    g.serialize(destination=args.output, format=args.fo)

def process(*args, **kwargs):
    """
    Run `arpa.arpafy` and display information about the process and results, 
    and return the results. Passes the given arguments to `arpa.arpafy`.
    """

    start_time = time.monotonic()

    res = arpafy(*args, **kwargs)

    end_time = time.monotonic()

    if res['errors']:
        print("Some errors occurred while querying:")
        for err in res['errors']:
            print(err)
    print("Processed {} triples, found {} matches ({} errors). Run time {}"
            .format(res['processed'], res['matches'], len(res['errors']), 
                timedelta(seconds=end_time-start_time)))

    return res


if __name__ == '__main__':
    main()
