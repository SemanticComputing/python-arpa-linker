from datetime import datetime
from arpa_linker.arpa import Arpa, process, log_to_file, parse_args
from rdflib import URIRef
from rdflib.namespace import SKOS
import logging
import re

log_to_file('persons.log', 'INFO')
logger = logging.getLogger('arpa_linker.arpa')


def validator(graph, s):
    def get_ranks(person):
        props = person.get('properties', {})
        return props.get('rank_label', []) + props.get('promotion_rank', [])

    def validate(text, results):
        if not results:
            return results
        date_uri = graph.value(s, URIRef("http://www.cidoc-crm.org/cidoc-crm/P4_has_time-span"))
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
                    pass
                else:
                    if start > death_date:
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
                if ('"Sotamies"' in ranks) and not re.findall("[Ss]otamie", text):
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
        return results

    return validate


def preprocessor(text, *args):
    if text.strip() == "Illalla venäläisten viimeiset evakuointialukset mm. Josif Stalin lähtivät Hangosta.":
        return ""
    text = text.replace("F. E. Sillanpää", "XXXXX")
    text = re.sub(r'Mannerheim(?!-)', 'XXX Carl Gustaf Mannerheim', text)
    text = text.replace("Ylipäällikkö", "Carl Gustaf Mannerheim")
    text = text.replace("Paavo Nurmi", "XXXXX")
    text = text.replace("T. M. Kivimäki", "Toivo Mikael Kivimäki")
    text = text.replace("Verner Viiklan", "Verner Viikla")
    text = text.replace("Heinrichsin", "Heinrichs")
    text = text.replace("Linderin", "Linder")
    text = text.replace("Karl Takkula", "K. Takkula")
    text = re.sub(r'(?<!Josif\W)Stalin(ille|in|iin)?\b', 'Josif Stalin', text)
    text = text.replace("Laiva Josif Stalin", "XXXXX")
    text = re.sub(r'(Aleksandra\W)?Kollontai(\b|lle|n|hin)', 'Alexandra Kollontay', text)
    text = re.sub(r'Blick(\b|ille|in)', 'Aarne Leopold Blick', text)
    text = text.replace("A.-E. Martola", "Ilmari Armas-Eino Martola")
    text = re.sub(r'(?<!alikersantti\W)Neno(nen|selle|sen)?\b', 'Vilho Petteri Nenonen', text)
    text = re.sub(r'[Mm]ajuri(\W+K\.\W*)? Kari(n|lle)?\b', 'everstiluutnantti Kari', text)
    # Needs tweaking for photos
    text = re.sub(r'(?<!M\.\W)Kallio(lle|n)?\b', 'XXX Kyösti Kallio', text)
    text = text.replace("Ryti", "XXX Risto Ryti")
    text = text.replace("Tanner", "XXX Väinö Tanner")
    text = text.replace("Niukkanen", "XXX Juho Niukkanen")
    text = text.replace("Söderhjelm", "XXX Johan Otto Söderhjelm")
    text = text.replace("Paasikivi", "XXX Juho Kusti Paasikivi")
    text = text.replace("Walden", "XXX Karl Rudolf Walden")
    text = text.replace("Cajander", "XXX Aimo Kaarlo Cajander")
    text = re.sub("[vV]ääpeli( Oiva)? Tuomi(nen|selle|sen)", "XXX Oiva Emil Kalervo Tuominen", text)

    return text


if __name__ == '__main__':
    args = parse_args()

    arpa = Arpa(args.arpa, args.no_duplicates, args.min_ngram, args.ignore)

    # Query the ARPA service, add the matches and serialize the graph to disk.
    process(args.input, args.fi, args.output, args.fo, args.tprop, arpa, args.prop,
            preprocessor=preprocessor, validator=validator, progress=True)

#process('input.ttl', 'turtle', 'output.ttl', 'turtle', DCTERMS['subject'],
#        Arpa('http://demo.seco.tkk.fi/arpa/sotasurmat'), validator=validator)
