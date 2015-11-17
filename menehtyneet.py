import re
import logging
from datetime import datetime
from arpa_linker.arpa import Arpa, process, log_to_file, parse_args
from rdflib.namespace import DCTERMS, SKOS

log_to_file('persons.log', 'INFO')
logger = logging.getLogger('arpa_linker.arpa')

LOW_RANKS = [
    'korpraali',
    'sotamies',
    'ylimatruusi',
    'lentosotamies',
    'panssarimies',
    'suojeluskuntasotamies',
    'aliupseerioppilas',
    'alokas',
    'matruusi',
    'tykkimies',
    'autosotamies',
    'ratsumies',
    'erikoisjääkäri',
    'ilmasuojelusotamies',
    'panssarijääkäri',
    'erikoisrajajääkäri',
    'viestimies',
    'rajajääkäri',
    'sotilaspoika',
    'rannikkojääkäri',
    'kaartinjääkäri',
    'suojelumies',
    'jääkäri',
    'luotsi',
    'merivartija',
    'suojeluskuntakorpraali',
    'ilmasuojelumies',
    'rakuuna',
    'pioneeri',
    'suojeluskunta-alokas'
]


def validator(graph, s):
    # Filter out the results where the person had died before the picture was taken.
    def validate(text, results):
        if not results:
            return results
        date_uri = graph.value(s, DCTERMS['created'])
        l = graph.value(s, SKOS.prefLabel)
        if date_uri:
            longest_matches = {}
            try:
                d = str(date_uri).split('time_')[1].split('-')
                start = datetime.strptime('-'.join(d[0:3]), "%Y-%m-%d").date()
            except ValueError:
                logger.warning("Invalid time-span URI: {}".format(date_uri))
                return results
            filtered = []
            for person in results:
                try:
                    death_date = datetime.strptime(
                        person['properties']['death_date'][0].split('^')[0],
                        '"%Y-%m-%d"').date()
                except (KeyError, ValueError):
                    logger.info("No death date found for {}".format(person.get('id')))
                    pass
                else:
                    if start > death_date:
                        logger.info(
                            "{} ({}) died ({}) before event start ({})".format(
                                person.get('label'), person.get('id'),
                                death_date, start))
                        continue
                # The person either died after the event or the date of death is unknown
                matches = person.get('matches')
                match_len = len(matches)
                count = 0
                match = True
                ranks = person.get('properties', {}).get('rank_label')
                if all(rank in LOW_RANKS for rank in ranks):
                    if not any(rank in match for rank in matches):
                        logger.info("Filtered out low rank with no rank match: {} {} ({}) with {} in {}".format(
                            ranks,
                            person.get('label'),
                            person.get('id'),
                            matches,
                            l))
                        continue
                for i, m in enumerate(matches, 1):
                    if match_len >= longest_matches.get(m, 0):
                        longest_matches[m] = match_len
                        count = count + 1

                    if count > 0 and i != count:
                        logger.warning("Partial longest match for {} ({}): {}".format(
                            person.get('label'), person.get('id'),
                            person.get('matches'), l))

                    if match_len < longest_matches.get(m, 0):
                        match = False
                        break
                if match:
                    logger.info("{} ({}) preliminarily accepted".format(
                        person.get('label'),
                        person.get('id')))
                    filtered.append(person)
                else:
                    logger.info("{} {} ({}) failed validation after matching {} in {} (in preliminary step)".format(
                        ranks,
                        person.get('label'),
                        person.get('id'),
                        matches,
                        l))

            res = []
            for p in filtered:
                match_len = len(p.get('matches'))
                if match_len >= longest_matches[p.get('matches')[0]]:
                    logger.info("{} {} ({}) passed validation, matching {} in {}".format(
                        p.get('properties', {}).get('rank_label', '(NO RANK)'),
                        p.get('label'),
                        p.get('id'),
                        p.get('matches'),
                        l))
                    res.append(p)
                else:
                    logger.info("{} {} ({}) failed validation after matching {} in {}".format(
                        p.get('properties', {}).get('rank_label', '(NO RANK)'),
                        p.get('label'),
                        p.get('id'),
                        p.get('matches'),
                        l))

            return res

    return validate


def preprocessor(text, *args):
    text = text.replace("F. E. Sillanpää", "Frans Emil Sillanpää")
    text = re.sub(r"\b[Yy]lipäällikk?ö(n|lle)?", "Carl Gustaf Mannerheim", text)
    text = re.sub(r'Marski(n|ll[ea])?', "Carl Gustaf Mannerheim", text)
    text = re.sub(r'(Suomen )?[Mm]arsalkk?a(n|ll[ea])?(?! Timoshenko)( Mannerheim)?',
            "Carl Gustaf Mannerheim", text)
    text = text.replace("Paavo Nurmi", "XXXXX")
    text = text.replace("Oech", "Oesch")
    text = text.replace("Väinö Tanner", "XXXXX")
    # text = text.replace("T. M. Kivimäki", "XXXXX")
    text = text.replace("Verner Viiklan", "Verner Viikla")
    text = text.replace("Heinrichsi(n|lle|lta)", "Heinrichs")
    text = re.sub(r"\b[Kk]enraali Heinrichs", "jalkaväenkenraali Heinrichs", text)
    text = text.replace("Linderin", "Linder")
    text = text.replace("Jautilainen", "Juutilainen")

    text = re.sub(r'[Kk]emraali', 'kenraali', text)

    text = re.sub(r'\b[Ee]v\.luutn\.', 'everstiluutnantti', text)
    text = re.sub(r'\b[Ee]v\.', 'eversti', text)
    text = re.sub(r'\b[Ll]uutn\.', 'luutnantti', text)

    text = re.sub(r'\b[Kk]orn\.', 'kornetti', text)

    text = re.sub(r'\b[Kk]apt\.', 'kapteeni', text)

    text = re.sub(r'\b[Ss]tm\.', 'sotamies', text)
    text = re.sub(r'\b[Kk]orpr\.', 'korpraali', text)


if __name__ == '__main__':
    args = parse_args()

    arpa = Arpa(args.arpa, args.no_duplicates, args.min_ngram, args.ignore)

    # Query the ARPA service, add the matches and serialize the graph to disk.
    process(args.input, args.fi, args.output, args.fo, args.tprop, arpa, args.prop,
            preprocessor=preprocessor, validator=validator, progress=True)
