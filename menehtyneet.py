from datetime import datetime
from arpa_linker.arpa import Arpa, process, log_to_file
from rdflib.namespace import DCTERMS

def validator(graph, s):
    # Filter out the results where the person had died before the picture was taken.
    def validate(text, results):
        if not results:
            return results
        pic_date = graph.value(s, DCTERMS['created'])
        if pic_date:
            try:
                pic_date = datetime.strptime(pic_date, "%Y-%m-%d").date()
            except ValueError:
                return results
            filtered = []
            for person in results:
                try:
                    death_date = datetime.strptime(
                            person['properties']['kuolinaika'][0].split('^')[0],
                            '"%Y-%m-%d"').date()
                except (KeyError, ValueError):
                    pass
                else:
                    if pic_date > death_date:
                        # The person died before the picture was taken, leave this one out
                        continue
                # The person either died after the picture was taken or the date of death is unknown
                filtered.append(person)
            return filtered
        # Picture date unknown, return the original results
        return results

    return validate

log_to_file('menehtyneet.log', 'INFO')

# Query the ARPA service, add the matches and serialize the graph to disk.
process('input.ttl', 'turtle', 'output.ttl', 'turtle', DCTERMS['subject'],
        Arpa('http://demo.seco.tkk.fi/arpa/sotasurmat'), validator=validator)
