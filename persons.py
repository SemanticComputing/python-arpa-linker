from datetime import datetime
from arpa_linker.arpa import Arpa, process, log_to_file, parse_args
from rdflib import URIRef
from rdflib.namespace import SKOS
import logging
import re

log_to_file('persons.log', 'INFO')
logger = logging.getLogger('arpa_linker.arpa')

dataset = None


def validator(graph, s):

    def get_s_start_date():
        def parse_date_as_list(d):
            return datetime.strptime('-'.join(d[0:3]), "%Y-%m-%d").date()

        def get_event_date():
            date_uri = graph.value(s, URIRef('http://www.cidoc-crm.org/cidoc-crm/P4_has_time-span'))
            try:
                d = str(date_uri).split('time_')[1].split('-')
                return parse_date_as_list(d)
            except ValueError:
                logger.warning("Invalid time-span URI: {}".format(date_uri))
                return None

        def get_photo_date():
            date_value = graph.value(s, URIRef('http://purl.org/dc/terms/created'))
            d = str(date_value).split('-')
            try:
                return parse_date_as_list(d)
            except ValueError:
                logger.warning("Invalid date: {}".format(date_value))
                return None

        if dataset == 'event':
            return get_event_date()
        elif dataset == 'photo':
            return get_photo_date()
        else:
            raise Exception('Dataset not defined or invalid')

    def get_ranks(person):
        props = person.get('properties', {})
        return props.get('rank_label', []) + props.get('promotion_rank', [])

    def validate(text, results):
        if not results:
            return results
        l = graph.value(s, SKOS.prefLabel)
        start = get_s_start_date()
        longest_matches = {}
        filtered = []
        for person in results:
            if person['label'] == 'Eric Väinö Tanner' \
                    or person['label'] == 'Erik Gustav Martin Heinrichs':
                logger.info("Filtering out person {}".format(person.get('id')))
                continue
            try:
                death_date = datetime.strptime(
                    person['properties']['death_date'][0].split('^')[0],
                    '"%Y-%m-%d"').date()
            except (KeyError, ValueError):
                logger.info("No death date found for {}".format(person.get('id')))
            else:
                if start and start > death_date:
                    logger.info(
                        "{} ({}) died ({}) before event start ({})".format(
                            person.get('label'), person.get('id'),
                            death_date, start))
                    continue
            # The person either died after the event or the date of death is unknown
            match_len = len(person.get('matches'))
            count = 0
            match = True
            for i, m in enumerate(person.get('matches'), 1):
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
                    get_ranks(person),
                    person.get('label'),
                    person.get('id'),
                    person.get('matches'),
                    l))

            res = []
            for p in filtered:
                match_len = len(p.get('matches'))
                ranks = get_ranks(p)
                if ('"Sotamies"' in ranks) and not re.findall(r"([Ss]otamie|[Ss]tm\b)", text):
                    logger.info("Filterin out private {} {} ({}), matched {} in {}".format(
                        ranks,
                        p.get('label'),
                        p.get('id'),
                        p.get('matches'),
                        l))
                elif match_len >= longest_matches[p.get('matches')[0]]:
                    logger.info("{} {} ({}) passed validation, matching {} in {}".format(
                        ranks,
                        p.get('label'),
                        p.get('id'),
                        p.get('matches'),
                        l))
                    res.append(p)
                else:
                    logger.info("{} {} ({}) failed validation after matching {} in {}".format(
                        ranks,
                        p.get('label'),
                        p.get('id'),
                        p.get('matches'),
                        l))

            return res
        # Event date unknown, return the original results
        logger.warning("Event date unknown: {} ({})".format(s, l))
        return results

    return validate

list_regex = '(?:(\w+)(?:,\W+))?' * 10 + '(\w+)?\W+ja\W+(\w+)'

_g_re = '[Kk]enraalit\W+' + list_regex
g_regex = re.compile(_g_re)

_m_re = '[Mm]inisterit(:)?\W+' + list_regex
m_regex = re.compile(_m_re)

def preprocessor(text, *args):
    if text.strip() == 'Illalla venäläisten viimeiset evakuointialukset mm. Josif Stalin lähtivät Hangosta.':
        return ''
    groups = []
    generals = g_regex.findall(text)
    if generals:
        generals = filter(bool, generals[0])
        for g, i in enumerate(generals, 1):
            groups.append('kenraali \\' + str(i))
        text = g_regex.sub(' '.join(groups))
    ministers = m_regex.findall(text)
    if ministers:
        ministers = filter(bool, ministers[0])
        for g, i in enumerate(ministers, 1):
            groups.append('ministeri \\' + str(i))
        text = g_regex.sub(' '.join(groups))
    text = re.sub(r'\b[Kk]enr(\.|aali) ', 'kenraaliluutnantti ', text)
    text = re.sub(r'\b[Kk]enr\.\b', 'kenraali#', text)
    text = re.sub(r'\b[Ee]v\.(?=(\b| ))', 'eversti#', text)
    text = re.sub(r'\b[Ll]uu(tn|nt)\.', 'luutnantti', text)
    text = re.sub(r'\b[Mm]aj\.', 'majuri', text)
    text = re.sub(r'\b[Kk]apt\.', 'kapteeni', text)
    text = text.replace('#', '')
    text = re.sub(r'\b[Ee]verstil\.', 'everstiluutnantti', text)
    text = re.sub(r'[Tt]ykistökenraali', 'tykistönkenraali', text)
    text = text.replace('F. E. Sillanpää', '##')
    text = re.sub(r'Mannerheim(?!-)', '## Carl Gustaf Mannerheim', text)
    text = re.sub(r'[Yy]lipäällikkö', 'Carl Gustaf Mannerheim', text)
    text = text.replace('Paavo Nurmi', '##')
    text = text.replace('T. M. Kivimäki', 'Toivo Mikael Kivimäki')
    text = text.replace('Verner Viiklan', 'Verner Viikla')
    text = text.replace('Heinrichsin', 'Heinrichs')
    text = text.replace('Linderin', 'Linder')
    text = text.replace('Karl Takkula', 'K. Takkula')
    text = re.sub(r'(?<!Josif\W)Stalin(ille|in|iin)?\b', 'Josif Stalin', text)
    text = text.replace('Laiva Josif Stalin', '##')
    text = re.sub(r'(Aleksandra\W)?Kollontai(\b|lle|n|hin)', 'Alexandra Kollontay', text)
    text = re.sub(r'Blick(\b|ille|in)', 'Aarne Leopold Blick', text)
    text = text.replace('A.-E. Martola', 'Ilmari Armas-Eino Martola')
    text = re.sub(r'(?<!alikersantti\W)Neno(nen|selle|sen)\b', '## kenraaliluutnantti Nenonen', text)
    text = re.sub(r'[Mm]ajuri(\W+K\.\W*)? Kari(n|lle)?\b', 'everstiluutnantti Kari', text)
    text = text.replace('majuri V.Tuompo', '##')
    text = text.replace('Tuompo, Viljo Einar', 'kenraaliluutnantti Tuompo')
    text = text.replace('Erfurth & Tuompo', 'Waldemar Erfurth ja kenraaliluutnantti Tuompo')
    text = text.replace('[Kk]enraali(majuri|luutnantti) Siilasvuo', 'Hjalmar Fridolf Siilasvuo')
    text = text.replace('Wuolijoki', '## Hella Wuolijoki')
    text = re.sub(r'[Mm]inisteri Koivisto', 'Juho Koivisto', text)
    # Needs tweaking for photos
    text = text.replace('G. Snellman', '## everstiluutnantti G. Snellman')
    text = text.replace('Ribbentrop', '## Joachim von_Ribbentrop')
    #text = text.replace('Kuusisen hallituksen', '## O. W. Kuusinen')
    #text = text.replace('Molotov', '## V. Molotov')  # not for photos
    #text = re.sub(r'(?<!M\.\W)Kallio(lle|n)?\b', '## Kyösti Kallio', text)
    text = re.sub(r'[Pp]residentti Kallio', '## Kyösti Kallio ##', text)
    text = re.sub(r'[Rr]va Kallio', '## Kaisa Kallio ##', text)
    text = text.replace('E. Mäkinen', '## kenraalimajuri Mäkinen')
    text = text.replace('Ryti', '## Risto Ryti')
    text = text.replace('Tanner', '## Väinö Tanner')
    text = text.replace('Niukkanen', '## Juho Niukkanen')
    text = text.replace('Söderhjelm', '## Johan Otto Söderhjelm')
    text = text.replace('Paasikivi', '## Juho Kusti Paasikivi')
    text = text.replace('Walden', '## Karl Rudolf Walden')
    text = text.replace('Cajander', '## Aimo Kaarlo Cajander')
    text = re.sub('[vV]ääpeli( Oiva)? Tuomi(nen|selle|sen)', '## Oiva Emil Kalervo Tuominen', text)

    return text


if __name__ == '__main__':
    args = parse_args()

    global dataset
    if args.tprop == 'http://purl.org/dc/terms/subject':
        logger.info('Handling as photos')
        dataset = 'photo'
    else:
        logger.info('Handling as events')
        dataset = 'event'

    arpa = Arpa(args.arpa, args.no_duplicates, args.min_ngram, args.ignore)

    # Query the ARPA service, add the matches and serialize the graph to disk.
    process(args.input, args.fi, args.output, args.fo, args.tprop, arpa, args.prop,
            preprocessor=preprocessor, validator=validator, progress=True)
