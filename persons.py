from datetime import datetime
from arpa_linker.arpa import Arpa, process, log_to_file
from rdflib import URIRef
import logging

log_to_file('persons.log', 'INFO')
logger = logging.getLogger('arpa_linker.arpa')

def validator(graph, s):
    # Filter out the results where the person had died before the picture was taken.
    def validate(text, results):
        if not results:
            return results
        date_uri = graph.value(s, URIRef("http://www.cidoc-crm.org/cidoc-crm/P4_has_time-span"))
        if date_uri:
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
                    logger.info("No death date found for {}".format(person))
                    pass
                else:
                    if start > death_date:
                        logger.info(
                            "Person {} died ({}) before event start ({})".format(
                                person, death_date, start))
                        continue
                # The person either died after the event or the date of death is unknown
                logger.info("Person {} passed validation".format(person))
                filtered.append(person)
            return filtered
        # Event date unknown, return the original results
        return results

    return validate

# Query the ARPA service, add the matches and serialize the graph to disk.
process('input.ttl', 'turtle', 'output.ttl', 'turtle',
        URIRef("http://www.cidoc-crm.org/cidoc-crm/P11_had_participant"),
        Arpa('http://demo.seco.tkk.fi/arpa/warsa_actor_persons'),
        validator=validator, progress=True)
#process('input.ttl', 'turtle', 'output.ttl', 'turtle', DCTERMS['subject'],
#        Arpa('http://demo.seco.tkk.fi/arpa/sotasurmat'), validator=validator)
