from arpa import arpafy, Arpa
from datetime import datetime
from rdflib import Graph
from rdflib.namespace import DCTERMS

def validator(graph, s):
    # Filter out the results where the person had died before the picture was taken.
    def validate(results):
        if not results:
            return results
        pic_date = graph.value(s, DCTERMS['created'])
        if pic_date:
            pic_date = datetime.strptime(pic_date, "%Y-%m-%d").date()
            filtered = []
            for person in results:
                try:
                    death_date = datetime.strptime(
                            person['properties']['kuolinaika'][0].split('^')[0],
                            '"%Y-%m-%d"').date()
                except KeyError:
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


graph = Graph()
graph.parse('input.ttl', format='turtle')

# Query the ARPA service and add the matches
res = arpafy(graph, DCTERMS['subject'],
        Arpa('http://demo.seco.tkk.fi/arpa/sotasurmat'), None, None, validator)

if res['errors']:
    print("Some errors occurred while querying:")
    for err in res['errors']:
        print(err)
print("Processed {} triples, found {} matches ({} errors)"
        .format(res['processed'], res['matches'], len(res['errors'])))

# Serialize the graph to disk
graph.serialize(destination='output.ttl', format='turtle')
