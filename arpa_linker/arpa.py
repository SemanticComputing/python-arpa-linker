"""
A module for linking resources to an RDF graph with an [ARPA](https://github.com/jiemakel/arpa) service.

## Requirements<a name="requirements"></a>
Python 3, [RDFLib](http://rdflib.readthedocs.org/en/latest/) and [Requests](http://docs.python-requests.org/en/latest/)

If you want to see a progress bar, you'll need [PyPrind](https://github.com/rasbt/pyprind).

## Usage<a name="usage"></a>

The module can be invoked as a script from the command line or by calling `arpa.arpafy` (or `arpa.process`) in your Python code.

<pre style="padding:5px">
usage: arpa.py [-h] [--fi INPUT_FORMAT] [--fo OUTPUT_FORMAT] [-n] [-c]
               [--rdf_class CLASS] [--prop PROPERTY]
               [--ignore [TERM [TERM ...]]] [--min_ngram N]
               [--no_duplicates [TYPE [TYPE ...]]] [-r N] [-w N]
               [--log_level {NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL}]
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
  -n, --new_graph       Add the ARPA results to a new graph instead of the
                        original. The output file contains all the triples of
                        the original graph by default. With this argument set
                        the output file will contain only the results.
  -c, --candidates_only
                        Get candidates (n-grams) only from ARPA.
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
  -r N, --retries N     The amount of retries per query if a HTTP error is
                        received. Default is 0.
  -w N, --wait N        The number of seconds to wait between retries. Only
                        has an effect if number of retries is set. Default is
                        1 second.
  --log_level {NOTSET,DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Logging level, default is INFO.
  --log_file LOG_FILE   The log file. Default is arpa_linker.log.
</pre>

The arguments can also be read from a file using "@" (example arg file [arpa.args](https://github.com/SemanticComputing/python-arpa-linker/blob/master/arpa.args)):

`$ python3 arpa.py @arpa.args`

## Examples<a name="examples"></a>

See [this repo](https://github.com/SemanticComputing/warsa-linkers) for code examples,
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

__all__ = ['Arpa', 'ArpaMimic', 'arpafy', 'process', 'process_graph', 'prune_candidates',
            'combine_candidates', 'map_results', 'log_to_file', 'post', 'parse_args',
            'main', 'LABEL_PROP', 'TYPE_PROP']

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


def _get_value(result):
    type_ = result.get('type', None)
    value = result.get('value', '')
    if type_ == 'literal':
        datatype = result.get('datatype', None)
        if datatype:
            return '"{}"^^{}'.format(value, datatype)
        return '"{}"'.format(value)
    if type_ == 'uri':
        return '<{}>'.format(value)
    return value


def map_results(results):
    """
    Map general SPARQL results to the format ARPA returns.

    Return the mapped results.

    `results` is the SPARQL result as a dict. Each row has to include an 'id' variable.
    """

    logger.debug('Mapping results {} to ARPA format'.format(results))

    res = []
    for obj in results['results']['bindings']:
        o_id = obj['id']['value']

        idx = next((index for (index, d) in enumerate(res) if d['id'] == o_id), None)
        if idx is None:
            props = {key: [_get_value(value)] for key, value in obj.items()}
            o = {
                'id': o_id,
                'label': obj.get('label', {}).get('value', ''),
                'matches': [obj.get('ngram', {}).get('value', '')],
                'properties': props
            }
            res.append(o)
        else:
            o = res[idx]
            ngram = obj.get('ngram', {}).get('value', '')
            if ngram not in o['matches']:
                o['matches'].append(ngram)
            for k, v in obj.items():
                p = o.get('properties').get(k, None)
                if p:
                    p.append(_get_value(v))
                else:
                    o['properties'][k] = [_get_value(v)]

    res = {'results': res}

    logger.debug('Mapped to: {}'.format(res))

    return res


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
            logger.debug('Success, received: {}'.format(res))
            return res


class Arpa:
    """Class representing the ARPA service"""

    def __init__(self, url, remove_duplicates=False, min_ngram_length=1, ignore=None,
            retries=0, wait_between_tries=1):
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
            logger.debug('Filtering candidates')
            get_len = lambda x: len(x.split())
            get_label = lambda x: x.lower()
            # No use in removing literal duplicates
            skip_remove_duplicates = True
        else:
            logger.debug('Filtering results')
            get_len = lambda x: len(x['properties']['ngram'][0].split())
            get_label = lambda x: x[LABEL_PROP].lower()
            skip_remove_duplicates = False

        return self._filter_results(results, get_len, get_label, skip_remove_duplicates)

    def query(self, text, candidates=False):
        """
        Query the ARPA service and return the response results as JSON

        Results will be filtered if a filter was specified at init.

        `text` is the text used in the query.

        If `candidates` is set, query for candidates only.
        """

        logger.debug('Query ARPA at {} with text {}'.format(self._url, text))

        if not text:
            raise ValueError('Empty ARPA query text')

        url = self._url + ('?cgen' if candidates else '')

        # Query the ARPA service with the text
        data = {'text': text}

        res = post(url, data, retries=self._retries, wait=self._wait)

        return self._filter(res.get('results', []), candidates)

    def extract_uris(self, results):
        """
        Get the URIs from results.

        `results` is the results as returned by `arpa.query`.
        """
        return [URIRef(x['id']) for x in results]

    def get_distinct_mentions(self, results):
        """
        Get distinct mentions (i.e. matches) that yielded results.

        `results` is the results as returned by `arpa.query`.
        """
        return {m for ml in [p['matches'] for p in results] for m in ml}

    def get_uri_matches(self, text, *args, validator=None, **kwargs):
        """
        Query ARPA and return a dict with a list of uris of resources that match the text.

        Return a dict where 'results' has the list of uris, 'mentions' has the mentions
        that yielded results, and 'pre_validation_mentions' has mentions that yielded
        results before running the `validator`.

        `text` is the text to use in the query.

        `validator` is an object that implements a `validate` method that takes
        the results and `text` (and any other parameters passed to this method)
        as parameters, and returns a subset of the results.
        """

        logger.info('Getting URI matches: {}'.format(text))

        results = self.query(text)

        pre_validation_mentions = set()
        post_validation_mentions = set()

        if validator and results:
            logger.debug('Validating results: {}'.format(results))
            pre_validation_mentions = self.get_distinct_mentions(results)
            logger.info('Distinct mentions before validation: {} ({})'.format(len(pre_validation_mentions), pre_validation_mentions))
            results = validator.validate(results, text, *args, **kwargs)

        if results:
            logger.info('Found matches {}'.format(results))
            post_validation_mentions = self.get_distinct_mentions(results)
            logger.info('Distinct mentions: {} ({})'.format(len(post_validation_mentions), post_validation_mentions))
            results = self.extract_uris(results)
        else:
            logger.info('No matches found'.format(text))

        return {
            'results': results,
            'mentions': post_validation_mentions,
            'pre_validation_mentions': pre_validation_mentions
        }

    def get_candidates(self, text, *args, **kwargs):
        """
        Get the candidates from `text` that would be used by the ARPA service
        to query for matches.

        A dict is returned for compatibility with `arpa.get_uri_matches`.

        Return a dict where 'results' has the candidates as a list of rdflib Literals.
        """

        if not text:
            raise ValueError('Empty ARPA query text')

        res = self.query(text, candidates=True)

        logger.debug('Received candidates: {}'.format(res))

        result = {'results': [Literal(candidate) for candidate in res]}

        return result


class ArpaMimic(Arpa):
    """
    Class that behaves like `arpa.Arpa` except that it queries a SPARQL endpoint
    instead of an ARPA service.
    """

    def __init__(self, query_template, *args, **kwargs):
        """
        Initialize the ArpaMimic instance.

        `query_template` is a SPARQL query template like ARPA uses.
        """

        self.query_template = query_template

        super().__init__(*args, **kwargs)

    def query(self, text, url_params=''):
        """
        Query a SPARQL endpoint and return the response results as JSON mapped
        as if returned by ARPA.

        `text` is the text used in the query.

        `url_params` is any URL parameters to be added to the URL.
        """

        logger.debug('Querying {} with text {} using ArpaMimic'.format(self._url, text))

        if not text:
            raise ValueError('Empty query text')

        query = self.query_template.replace('<VALUES>', text)

        url = self._url + url_params

        # Query the endpoint with the text
        data = {'query': query}

        res = post(url, data, retries=self._retries, wait=self._wait)

        res = map_results(res)

        return self._filter(res.get('results', []))


class Bar:
    """
    Mock progress bar implementation
    """

    def __init__(self, n, *args, **kwargs):
        self.n = n

    def update(self, *args, **kwargs):
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


def _get_subgraph(graph, source_prop, rdf_class=None):
    subgraph = Graph()

    if rdf_class:
        # Filter out subjects that are not of the given type
        for s in graph.subjects(RDF.type, rdf_class):
            subgraph += graph.triples((s, source_prop, None))
    else:
        subgraph += graph.triples((None, source_prop, None))

    return subgraph


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

    `validator` is an object with a `validate` method that takes the ARPA results, query text, and the processed
    subject as parameters, and returns a subset of the results (that have been validated based on the subject,
    graph and results). Optional.

    If `candidates_only` is set, get candidates (n-grams) only from ARPA.

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

    subgraph = _get_subgraph(graph, source_prop, rdf_class)

    triple_match_count = 0
    subject_match_count = 0
    pre_validation_mention_count = 0
    post_validation_mention_count = 0
    errors = []

    bar = get_bar(len(subgraph), progress)

    for s, o in subgraph.subject_objects():
        o = preprocessor(o, s, graph) if preprocessor else o
        try:
            result_dict = get_results(o, s, validator=validator)
        except (HTTPError, ValueError) as e:
            logger.exception('Error getting matches from ARPA')
            errors.append(e)
        else:
            results = result_dict['results']
            triple_match_count += len(results)
            pre_validation_mention_count += len(result_dict.get('pre_validation_mentions', []))
            if results:
                subject_match_count += 1
                post_validation_mention_count += len(result_dict.get('mentions', []))
                # Add each result as a value of the target property
                for result in results:
                    output_graph.add((s, target_prop, result))
        bar.update()

    res = {
        'graph': output_graph,
        'processed': len(subgraph),
        'matches': triple_match_count,
        'subjects_matched': subject_match_count,
        'pre_validation_mention_count': pre_validation_mention_count,
        'post_validation_mention_count': post_validation_mention_count,
        'errors': errors
    }

    logger.info('Processed {} triples, found {} matches from {} mentions'
                ' with {} total mentions ({} errors)'
                .format(res['processed'], res['matches'], res['post_validation_mention_count'],
                    res['pre_validation_mention_count'], len(res['errors'])))

    return res


def prune_candidates(graph, source_prop, pruner, rdf_class=None,
            output_graph=None, progress=None):
    """
    Prune undesired candidates.

    Return a dict with the amount of candidates left after pruning (result_count),
    and the resulting graph (graph).

    `graph` is the graph containing the candidates. Will be modified if `output_graph`
    is not given.

    `source_prop` is the property in the graph that has the candidates as its value.

    `pruner` is a function that receives a single candidate as string and returns
    a falsey value if the candidate should not be added to the output graph, and
    otherwise a string (the candidate, possibly modified) that should be added
    to the output graph.

    If `rdf_class` is given, only go through instances of this type.

    `output_graph` is the graph to which the results should be added.
    If not given, the results will be added to the input `graph`,
    and the old candidates removed.
    """

    logger.info('Pruning candidates')

    if output_graph is None:
        output_graph = graph

    subgraph = _get_subgraph(graph, source_prop, rdf_class)

    bar = get_bar(len(subgraph), progress)

    result_count = 0

    for s, o in subgraph.subject_objects():
        result = pruner(str(o))
        # Remove the original candidate
        output_graph.remove((s, source_prop, o))
        if result:
            result_count += 1
            # Add the pruned candidate to the output graph
            output_graph.add((s, source_prop, Literal(result)))
        bar.update()

    res = {
        'graph': output_graph,
        'result_count': result_count
    }

    logger.info('Candidate pruning complete')

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
    argparser.add_argument("-c", "--candidates_only", action="store_true",
        help="""Get candidates (n-grams) only from ARPA.""")
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
    argparser.add_argument("-w", "--wait", default=1, metavar="N", type=int,
        help="""The number of seconds to wait between retries. Only has an effect if number
        of retries is set. Default is 1 second.""")
    argparser.add_argument("--log_level", default="INFO",
        choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level, default is INFO.")
    argparser.add_argument("--log_file", default="arpa_linker.log",
        help="The log file. Default is arpa_linker.log.")

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


def combine_values(values):
    """Combine values into a single string"""

    values = [str(o).replace('"', '\\"') for o in values]
    return '"' + '" "'.join(values) + '"'


def combine_candidates(graph, prop, output_graph=None, rdf_class=None, progress=None):
    """
    Combine each subject's candidates into a single string.

    Return the resulting graph.

    `graph` is the graph containing the candidates. Will be modified if `output_graph`
    is not given.

    `prop` is the URIRef of the property containing the candidates.

    `output_graph` is the graph to which the results should be added.
    If not given, `graph` will be modified.

    If `rdf_class` is given, only go through instances of this type.

    If `progress` is set, display a progress bar.
    """

    subgraph = _get_subgraph(graph, prop, rdf_class)

    logger.info('Combining candidates')

    if output_graph is None:
        output_graph = graph

    subjects = subgraph.subjects()
    bar = get_bar(len(subgraph), progress)

    for s in subjects:
        combined = combine_values(subgraph.objects(s))
        # Remove the original candidate
        output_graph.remove((s, None, None))
        output_graph.add((s, prop, Literal(combined)))
        bar.update()

    logger.info('Candidates combined succesfully')

    return output_graph


def process_graph(graph, target_prop=None, arpa=None, new_graph=False, prune=False, join_candidates=False,
        run_arpafy=True, source_prop=None, rdf_class=None, pruner=None, progress=None, **kwargs):
    """
    Convenience function for running different tasks related to linking.

    `graph` is the graph to be processed.

    `target_prop` is the property name that is used for saving the link.
    Used only if `run_arpafy` is True.

    `arpa` is the `arpa.Arpa` class instance.
    Used only if `run_arpafy` is True.

    If `new_graph` is set, use a new empty graph for adding the results.

    If `prune` is set, prune candidates using `arpa.prune_candidates`.

    If `join_candidates` is set, combine candidates into a single value using
    `arpa.combine_candidates`.

    Setting `run_arpafy` to False will skip running `arpa.arpafy`.
    Useful with `join_candidates`.

    `source_prop` is the property URI that contains the values to be processed.

    For `pruner` see `arpa.prune_candidates`.

    If `progress` is `True`, show a progress bar. Requires pyprind.

    All other arguments are passed to `arpa.arpafy` (if run).

    Return the results dict as returned by `arpa.arpafy`.
    """

    if new_graph:
        logger.debug('Output to new graph')
        output_graph = Graph()
        output_graph.namespace_manager = graph.namespace_manager
    else:
        output_graph = graph

    logger.info('Begin processing')
    start_time = time.monotonic()

    if prune:
        logger.info('Prune candidates')
        res = prune_candidates(graph, source_prop, pruner,
                rdf_class=rdf_class, output_graph=output_graph,
                progress=progress)
        graph = res['graph']

    if join_candidates:
        logger.debug('Combine candidates')
        output_graph = combine_candidates(graph, source_prop,
                output_graph=output_graph, rdf_class=rdf_class,
                progress=progress)
        graph = output_graph
        res = {'graph': output_graph}

    if run_arpafy:
        logger.info('Start arpafy')
        res = arpafy(graph, target_prop=target_prop, arpa=arpa, source_prop=source_prop, rdf_class=rdf_class,
                output_graph=output_graph, progress=progress, **kwargs)

    end_time = time.monotonic()
    logger.info('Processing complete, runtime {}'.
            format(timedelta(seconds=(end_time - start_time))))

    return res


def process(input_file, input_format, output_file, output_format, *args,
        validator_class=None, **kwargs):
    """
    Parse the given input file, run `arpa.arpafy`, and serialize the resulting
    graph on disk.

    `input_file` is the name of the rdf file to be parsed.

    `input_format` is the input file format.

    `output_file` is the output file name.

    `output_format` is the output file format.

    `validator_class` is class that takes the input graph as parameter, and implements
    a `validate` method. See `arpa.arpafy` for more information.
    This overrides any validator object given as the `arpa.arpafy` `validator` parameter.

    All other arguments are passed to `arpa.process_graph`.

    Return the results dict as returned by `arpa.arpafy`.
    """

    g = Graph()
    logger.info('Parsing file {}'.format(input_file))
    g.parse(input_file, format=input_format)
    logger.info('Parsing complete')

    if validator_class:
        kwargs['validator'] = validator_class(g)

    res = process_graph(g, *args, **kwargs)

    output_graph = res['graph']

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

    log_to_file(args.log_file, args.log_level)

    arpa = Arpa(args.arpa, args.no_duplicates, args.min_ngram, args.ignore, args.retries)

    # Query the ARPA service, add the matches and serialize graph to disk
    process(args.input, args.fi, args.output, args.fo, target_prop=args.tprop,
            arpa=arpa, source_prop=args.prop, rdf_class=args.rdf_class,
            new_graph=args.new_graph, progress=True, candidates_only=args.candidates_only)

    logging.shutdown()


if __name__ == '__main__':
    main(sys.argv[1:])
