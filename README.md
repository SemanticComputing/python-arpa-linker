# ARPA linker
Tool for linking resources with ARPA

```
usage: arpa.py [-h] [--fi FI] [--fo FO] [--rdfclass RDFCLASS] [--prop PROP] input output tprop arpa

Link resources with ARPA.

positional arguments:
    input                Input rdf file
    output               Output file
        tprop                Target property for the matches
        arpa                 ARPA service URL

optional arguments:
    -h, --help           show this help message and exit
    --fi FI              Input file format (rdflib parser). Will be guessed if
                            omitted.
    --fo FO              Output file format (rdflib serializer). Default is
                            turtle.
    --rdfclass RDFCLASS  Process only instances of the given class
    --prop PROP          Property that's value is to be used in matching.
                            Default is skos:prefLabel.
```
