"""
A module for linking resources to an RDF graph with an [ARPA](https://github.com/jiemakel/arpa) service.

## Requirements<a name="requirements"></a>
Python 3, [RDFLib](http://rdflib.readthedocs.org/en/latest/) and [Requests](http://docs.python-requests.org/en/latest/)

If you want to see a progress bar, you'll need [PyPrind](https://github.com/rasbt/pyprind).

## Usage<a name="usage"></a>

The module can be invoked as a script from the command line or by calling `arpa.arpafy` (or `arpa.process`) in your Python code.

<pre>
usage: arpa.py [-h] [--fi INPUT_FORMAT]
            [--fo OUTPUT_FORMAT] [-n]
            [--rdf_class CLASS] [--prop PROPERTY]
            [--ignore [TERM [TERM ...]]] [--min_ngram N]
            [--no_duplicates [TYPE [TYPE ...]]] [-r N]
            [--log_level
                {NOTSET,DEBUG,INFO,WARNING, ERROR,CRITICAL}]
            input output target_property arpa

Link resources to an RDF graph with ARPA.

positional arguments:
input                 Input rdf file
output                Output file
target_property       Target property for the matches
arpa                  ARPA service URL

optional arguments:
-h, --help            show this help message and exit
--fi INPUT_FORMAT     Input file format (rdflib parser).
                      Will be guessed if omitted.
--fo OUTPUT_FORMAT    Output file format (rdflib
                      serializer). Default is turtle.
-n, --new_graph       Add the ARPA results to a new graph
                      instead of the original. The output
                      file contains all the triples of the
                      original graph by default. With this
                      argument set the output file will
                      contain only the results.
--rdf_class CLASS     Process only subjects of the given
                      type (goes through all subjects by
                      default).
--prop PROPERTY       Property that's value is to be used
                      in matching.
                      Default is skos:prefLabel.
--ignore [TERM [TERM ...]]
                      Terms that should be ignored even
                      if matched
--min_ngram N         The minimum ngram length that is
                      considered a match. Default is 1.
--no_duplicates [TYPE [TYPE ...]]
                      Remove duplicate matches based on
                      the 'label' returned by the ARPA
                      service. Here 'duplicate' means a
                      subject with the same label as
                      another subject in the same result
                      set. A list of types can be given
                      with this argument. If given,
                      prioritize matches based on it
                      - the first given type will get the
                      highest priority and so on. Note
                      that the response from the service
                      has to include a 'type' variable for
                      this to work.
-r N, --retries N     The amount of retries per query if
                      a HTTP error is received.
                      Default is 0.
--log_level {NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL}
                      Logging level, default is INFO.
                      The log file is arpa_linker.log.
</pre>

The arguments can also be read from a file using "@" (example arg file [arpa.args](https://github.com/SemanticComputing/python-arpa-linker/blob/master/arpa.args)):

`$ python3 arpa.py @arpa.args`

## Examples<a name="examples"></a>

See [menehtyneet.py](https://github.com/SemanticComputing/python-arpa-linker/blob/master/menehtyneet.py) and
[places.py](https://github.com/SemanticComputing/python-arpa-linker/blob/master/places.py) for code examples
and [arpa.args](https://github.com/SemanticComputing/python-arpa-linker/blob/master/arpa.args) for an example arg file.
"""

import sys
import argparse
import requests
import time
import logging
from datetime import timedelta
from requests.exceptions import HTTPError
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, SKOS
from rdflib.util import guess_format

__all__ = ['Arpa', 'arpafy', 'process', 'log_to_file', 'parse_args', 'main', 'LABEL_PROP', 'TYPE_PROP']

LABEL_PROP = 'label'
"""The name of the property containing the label of the match in the ARPA results."""

TYPE_PROP = 'type'
"""
The name of the property containing the type of the match in the ARPA results->properties.
Only needed for prioritized duplicate removal.
"""

logger = logging.getLogger(__name__)

# Hide requests INFO logging spam
requests_logger = logging.getLogger('requests')
requests_logger.setLevel(logging.WARNING)


def post(url, data, retries=0, wait=1):
    """
    Send a post request to the given URL with the given data, expecting a JSON response.
    Throws a HTTPError if the request fails (after retries, if any) or if JSON
    parsing fails.

    `url` is the URL to send the request to.

    `data` is a dict containing the data to send to the URL.

    `retries` is the number of retries to attempt if the request fails. Optional.

    `wait` is the number of seconds to wait between retries. Optional, default is 1 second.
    Has no effect if `retries` is not set.
    """

    if retries < 0:
        raise ValueError('Invalid amount of retries: {}'.format(retries))
    if wait < 0:
        raise ValueError('Invalid retry wait time: {}'.format(wait))

    tries = retries + 1

    while tries:
        logger.debug('Sending request to {} with data: {}'.format(url, data))
        res = requests.post(url, data)
        try:
            res.raise_for_status()
            res = res.json()
        except (HTTPError, ValueError) as e:
            tries -= 1
            if tries:
                logger.warning('Received error ({}) from {} with request data: {}.'
                        .format(e, url, data))
                logger.warning('Waiting {} seconds before retrying'.format(wait))
                time.sleep(wait)
                continue
            elif retries:
                    logger.warning('Error {}, out of retries.'.format(e))
            raise HTTPError('Error ({}) from {} with request data: {}.'.format(e, url, data))
        else:
            # Success
            return res


class Arpa:
    """Class representing the ARPA service"""

    def __init__(self, url, remove_duplicates=False, min_ngram_length=1, ignore=None, retries=0,
            wait_between_tries=1):
        """
        Initialize the Arpa service object.

        `url` is the ARPA service url.

        If `remove_duplicates` is `True`, choose only one subject out of all the
        matched subjects that have the same label (arbitrarily).
        If, instead, the value is a list or a tuple, assume that it represents
        a list of class names and prefer those classes when choosing
        the subject. The ARPA results must include a property (`arpa.TYPE_PROP`)
        that has the class of the match as the value. Optional.

        `min_ngram_length` is the minimum ngram match length that will be included when
        returning the query results. Optional.

        `ignore` is a list of matches that should be removed from the results (case insensitive).
        Optional.

        `retries` is the number of retries per query. Optional.

        `wait_between_tries` is the amount of times in seconds to wait between retries.
        Optional, default is 1 second. Has no effect if `retries` is not set.
        """

        logger.debug('Initialize Arpa instance')

        if retries < 0:
            raise ValueError('Number of retries has to be a non-negative number, got {}'
                    .format(retries))
        if wait_between_tries < 0:
            raise ValueError('Retry wait time has to be a non-negative number, got {}'
                    .format(wait_between_tries))

        self._retries = retries

        self._url = url
        self._ignore = [s.lower() for s in ignore or []]
        self._min_ngram_length = min_ngram_length
        self._wait = wait_between_tries

        if type(remove_duplicates) == bool:
            self._no_duplicates = remove_duplicates
        else:
            self._no_duplicates = tuple('<{}>'.format(x) for x in remove_duplicates)

        logger.debug('ARPA ignore set to {}'.format(self._ignore))
        logger.debug('ARPA url set to {}'.format(self._url))
        logger.debug('ARPA min_ngram_length set to {}'.format(self._min_ngram_length))
        logger.debug('ARPA no_duplicates set to {}'.format(self._no_duplicates))
        logger.debug('ARPA retries set to {}'.format(self._retries))

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
        if self._no_duplicates is True:
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

    def _filter_results(self, results, get_len, get_label, skip_remove_duplicates=False):
        """
        Internal filter function used by `arpa.Arpa._filter`.
        """

        # Filter ignored results
        if self._ignore:
            results = [x for x in results if get_label(x) not in self._ignore]

        # Filter by minimum ngram length
        if self._min_ngram_length > 1:
            results = [x for x in results if get_len(x) >= self._min_ngram_length]

        # Remove duplicates unless requested to skip
        if skip_remove_duplicates:
            return results
        return self._remove_duplicates(results)

    def _filter(self, results, candidates=False):
        """
        Filter matches based on `self._ignore` and remove matches that are
        for ngrams with length less than `self.min_ngram_length`.

        Return the response with the ignored matches removed.

        `results` is the parsed ARPA service results.

        `candidates` is whether or not the results contain just the candidates.
        """

        if candidates:
            get_len = lambda x: len(x.split())
            get_label = lambda x: x.lower()
            # No use in removing literal duplicates
            skip_remove_duplicates = True
        else:
            get_len = lambda x: len(x['properties']['ngram'][0].split())
            get_label = lambda x: x[LABEL_PROP].lower()
            skip_remove_duplicates = False

        return self._filter_results(results, get_len, get_label, skip_remove_duplicates)

    def _sanitize(self, text):
        # Remove quotation marks and brackets - ARPA can return an error if they're present
        if not text:
            return text
        return text.replace('"', '').replace('(', '').replace(')', '')

    def query(self, text, url_params=''):
        """
        Query the ARPA service and return the response results as JSON

        `text` is the text used in the query.

        `url_params` is any URL parameters to be added to the ARPA URL, e.g. '?cgen'.
        """

        text = self._sanitize(text)
        if not text:
            raise ValueError('Empty ARPA query text')

        url = self._url + url_params

        # Query the ARPA service with the text
        data = {'text': text}

        res = post(url, data, retries=self._retries, wait=self._wait)

        return res.get('results', None)

    def get_uri_matches(self, text, validator=None):
        """
        Query ARPA and return a list of uris for resources that match the text.

        `text` is the text to use in the query.

        `validator` is a function that takes the ARPA results as parameter and returns
        validated results.
        """

        results = self._filter(self.query(text))

        if validator and results:
            logger.debug('Validating results: {}'.format(results))
            results = validator(text, results)

        if results:
            logger.debug('Found matches {}'.format(results))
            res = [URIRef(x['id']) for x in results]
        else:
            logger.debug('No matches for {}'.format(text))
            res = []

        return res

    def get_candidates(self, text, *args, **kwargs):
        """
        Get the candidates from `text` that would be used by the ARPA service
        to query for matches.

        Return the candidates as JSON.
        """

        text = self._sanitize(text)
        if not text:
            raise ValueError('Empty ARPA query text')

        res = self._filter(self.query(text, '?cgen'), candidates=True)

        logger.debug('Received candidates: {}'.format(res))

        result = [Literal(candidate) for candidate in res]

        return result


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

    If `use_pyprind` is true, try to return a `pyprind.ProgBar` instance. Otherwise,
    return a mock progress bar.
    """

    if use_pyprind:
        try:
            import pyprind
            logger.debug('Using pyprind progress bar')
            return pyprind.ProgBar(n)
        except ImportError:
            logger.warning('Tried to use pyprind progress bar but pyprind is not available')
            pass

    logger.debug('Using mock progress bar')
    return Bar(n)


def arpafy(graph, target_prop, arpa, source_prop=None, rdf_class=None,
            output_graph=None, preprocessor=None, validator=None,
            candidates_only=False, progress=None):
    """
    Link a property to resources using ARPA. Modify the graph in place,
    unless `output_graph` is given.

    Return a dict with the amount of processed triples (processed), the resulting graph (graph),
    match count (matches) and errors encountered (errors).

    `graph` is the graph to link (will be modified unless `output_graph` is defined.

    `target_prop` is the property name that is used for saving the link.

    `arpa` is the `arpa.Arpa` class instance.

    `source_prop` is the property that's value will be used when querying ARPA (if omitted, skos:prefLabel is used).

    If `rdf_class` is given, only go through instances of this type.

    `output_graph` is the graph to which the results should be added. If not given, the results will be added
    to the input `graph`.

    `preprocessor` is an optional function that processes the query text before it is used in the ARPA query.
    It receives whatever is the value of `source_prop` for the current subject, the current subject, and the graph.

    `validator` is a function that takes a graph and a subject as parameter and returns a function
    that takes the query text and the ARPA results as parameter and returns a subset of those results
    (that have been validated based on the subject, graph and results). Optional.
    This is a function and not an object because of reasons.

    If `progress` is `True`, show a progress bar. Requires pyprind.
    """

    if source_prop is None:
        source_prop = SKOS['prefLabel']
    if output_graph is None:
        output_graph = graph
    if candidates_only:
        get_results = arpa.get_candidates
    else:
        get_results = arpa.get_uri_matches

    subgraph = Graph()

    if rdf_class:
        # Filter out subjects that are not of the given type
        for s in graph.subjects(RDF.type, rdf_class):
            subgraph += graph.triples((s, source_prop, None))
    else:
        subgraph += graph.triples((None, source_prop, None))

    triple_match_count = 0
    subject_match_count = 0
    errors = []

    bar = get_bar(len(subgraph), progress)

    for s, o in subgraph.subject_objects():
        o = preprocessor(o, s, graph) if preprocessor else o
        args = (o, validator(graph, s)) if validator else (o,)
        try:
            results = get_results(*args)
        except (HTTPError, ValueError) as e:
            logger.exception('Error getting matches from ARPA')
            errors.append(e)
        else:
            triple_match_count += len(results)
            if results:
                subject_match_count += 1
                # Add each result as a value of the target property
                for result in results:
                    output_graph.add((s, target_prop, result))
        bar.update()

    res = {
        'graph': output_graph,
        'processed': len(subgraph),
        'matches': triple_match_count,
        'subjects_matched': subject_match_count,
        'errors': errors
    }

    logger.info('Processed {} triples, found {} matches ({} errors)'
                .format(res['processed'], res['matches'], len(res['errors'])))

    return res


def log_to_file(file_name, level):
    """
    Convenience function for setting up logging to file.

    `file_name` is the log file name.

    `level` is the log level name (string).
    """

    logger.setLevel(getattr(logging, level.upper()))
    handler = logging.FileHandler(file_name)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


def parse_args(args):
    """
    Parse command line arguments. See [Usage](#usage) (or the source code) for details.

    `args` is the list of command line arguments.
    """

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
    argparser.add_argument("-n", "--new_graph", action="store_true",
        help="""Add the ARPA results to a new graph instead of the original. The output file
        contains all the triples of the original graph by default. With this argument set
        the output file will contain only the results.""")
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
    argparser.add_argument("-r", "--retries", default=0, metavar="N", type=int,
        help="The amount of retries per query if a HTTP error is received. Default is 0.")
    argparser.add_argument("--log_level", default="INFO",
        choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level, default is INFO. The log file is arpa_linker.log.")

    args = argparser.parse_args(args)

    if not args.fi:
        args.fi = guess_format(args.input)

    if args.prop:
        args.prop = URIRef(args.prop)

    if args.rdf_class:
        args.rdf_class = URIRef(args.rdf_class)

    args.tprop = URIRef(args.tprop)

    if args.no_duplicates == []:
        args.no_duplicates = True

    return args


def process(input_file, input_format, output_file, output_format, *args,
        new_graph=False, **kwargs):
    """
    Parse the given input file, run `arpa.arpafy`, and serialize the resulting
    graph on disk.

    `input_file` is the name of the rdf file to be parsed.

    `output_file` is the output file name.

    `output_format` is the output file format.

    If `new_graph` is set, use a new empty graph for adding the results.

    All other arguments are passed to `arpa.arpafy`.

    Return the results dict as returned by `arpa.arpafy`.
    """

    g = Graph()
    logger.info('Parsing file {}'.format(input_file))
    g.parse(input_file, format=input_format)
    logger.info('Parsing complete')

    if new_graph:
        output_graph = Graph()
        output_graph.namespace_manager = g.namespace_manager
    else:
        output_graph = g
    kwargs['output_graph'] = output_graph

    logger.info('Begin processing')
    start_time = time.monotonic()

    res = arpafy(g, *args, **kwargs)

    end_time = time.monotonic()

    logger.info('Processing complete, runtime {}'.
            format(timedelta(seconds=(end_time - start_time))))

    logger.info('Serializing graph as {}'.format(output_file))
    output_graph.serialize(destination=output_file, format=output_format)
    logger.info('Serialization complete')

    return res


def main(args):
    """
    Main function for running via the command line.

    `args` is the list of command line arguments.
    """

    args = parse_args(args)

    log_to_file('arpa_linker.log', args.log_level)

    arpa = Arpa(args.arpa, args.no_duplicates, args.min_ngram, args.ignore, args.retries)

    # Query the ARPA service, add the matches and serialize graph to disk
    process(args.input, args.fi, args.output, args.fo, args.tprop, arpa,
            args.prop, args.rdf_class, new_graph=args.new_graph, progress=True)

    logging.shutdown()


if __name__ == '__main__':
    main(sys.argv[1:])
