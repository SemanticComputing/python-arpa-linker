from arpa_linker.arpa import Arpa, ArpaMimic, process, log_to_file, parse_args
import time
import logging

logger = logging.getLogger('arpa_linker.arpa')


def init_log(name, level, file_prefix=''):
    log_to_file('{}{}_{}.log'.format(file_prefix, name, time.strftime('%Y%m%d_%H%M%S')), level)


def process_stage(argv, ignore=None, validator_class=None, preprocessor=None, pruner=None,
        remove_duplicates=False, log_level='INFO'):

    if argv[1] == 'prune':
        # Remove ngrams that will not match anything for sure
        args = parse_args(argv[2:])
        init_log('_prune', log_level, args.log_file)
        process(args.input, args.fi, args.output, args.fo, args.tprop, prune=True,
                pruner=pruner, source_prop=args.prop, rdf_class=args.rdf_class,
                new_graph=args.new_graph, run_arpafy=False, progress=True)

    elif argv[1] == 'join':
        # Merge ngrams into a single value
        args = parse_args(argv[2:])
        process(args.input, args.fi, args.output, args.fo, args.tprop, source_prop=args.prop,
                rdf_class=args.rdf_class, new_graph=args.new_graph, join_candidates=True,
                run_arpafy=False, progress=True)

    elif 'disambiguate' in argv[1]:
        # Link (with possible validation)
        args = parse_args(argv[3:])

        f = open(argv[2])
        qry = f.read()
        f.close()

        if argv[1] == 'disambiguate_validate':
            init_log('_validate', log_level, args.log_file)
            val = validator_class
            dupl = remove_duplicates
        else:
            init_log('_disambiguate', log_level, args.log_file)
            val = None
            dupl = False

        arpa = ArpaMimic(qry, args.arpa, dupl, args.min_ngram, ignore,
                retries=args.retries, wait_between_tries=args.wait)

        process(args.input, args.fi, args.output, args.fo, args.tprop, arpa=arpa,
                validator_class=val, source_prop=args.prop, rdf_class=args.rdf_class,
                new_graph=args.new_graph, progress=True)

    elif 'raw' in argv[1]:
        # No preprocessing or validation

        args = parse_args(argv[2:])
        init_log('_raw', log_level, args.log_file)
        arpa = Arpa(args.arpa, retries=args.retries, wait_between_tries=args.wait)

        # Query the ARPA service, add the matches and serialize the graph to disk.
        process(args.input, args.fi, args.output, args.fo, args.tprop, arpa,
                source_prop=args.prop, rdf_class=args.rdf_class, new_graph=args.new_graph,
                progress=True, candidates_only=args.candidates_only)

    else:
        args = parse_args(argv[1:])
        init_log('_arpa', log_level, args.log_file)
        arpa = Arpa(args.arpa, args.no_duplicates, args.min_ngram, ignore,
                retries=args.retries, wait_between_tries=args.wait)

        # Query the ARPA service, add the matches and serialize the graph to disk.
        process(args.input, args.fi, args.output, args.fo, args.tprop, arpa,
                source_prop=args.prop, rdf_class=args.rdf_class, new_graph=args.new_graph,
                preprocessor=preprocessor, validator_class=validator_class, progress=True,
                candidates_only=args.candidates_only)


if __name__ == '__main__':
    import sys
    process_stage(sys.argv)
