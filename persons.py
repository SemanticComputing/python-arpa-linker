from datetime import datetime
from arpa_linker.arpa import Arpa, process, log_to_file
from rdflib import URIRef
from rdflib.namespace import SKOS
import logging
import re

log_to_file('persons.log', 'INFO')
logger = logging.getLogger('arpa_linker.arpa')


def validator(graph, s):
    # Filter out the results where the person had died before the picture was taken.
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
                        person.get('properties', {}).get('rank_label', '(NO RANK)'),
                        person.get('label'),
                        person.get('id'),
                        person.get('matches'),
                        l))

            res = []
            for p in filtered:
                match_len = len(p.get('matches'))
                ranks = p.get('properties', {}).get('rank_label', '(NO RANK)')
                if len(filtered) > 1 and ('"Sotamies"' in ranks):
                    logger.info("Filterin out private {} {} ({}), matched {} in {}".format(
                        ranks,
                        p.get('label'),
                        p.get('id'),
                        p.get('matches'),
                        l))
                elif match_len >= longest_matches[p.get('matches')[0]]:
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
        # Event date unknown, return the original results
        return results

    return validate


def preprocessor(text, *args):
    text = text.replace("F. E. Sillanpää", "Frans Emil Sillanpää")
    text = text.replace("Ylipäällikkö", "Carl Gustaf Mannerheim")
    text = text.replace("Paavo Nurmi", "XXXXX")
    text = text.replace("Verner Viiklan", "Verner Viikla")

    return text


# Query the ARPA service, add the matches and serialize the graph to disk.
process('input.ttl', 'turtle', 'output.ttl', 'turtle',
        URIRef("http://www.cidoc-crm.org/cidoc-crm/P11_had_participant"),
        Arpa('http://demo.seco.tkk.fi/arpa/warsa_actor_persons'),
        preprocessor=preprocessor, validator=validator, progress=True)
#process('input.ttl', 'turtle', 'output.ttl', 'turtle', DCTERMS['subject'],
#        Arpa('http://demo.seco.tkk.fi/arpa/sotasurmat'), validator=validator)
