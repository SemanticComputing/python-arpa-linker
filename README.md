# ARPA linker
Tool for linking resources to an RDF graph with an [ARPA](https://github.com/jiemakel/arpa) service

```
usage: arpa.py [-h] [--fi INPUT_FORMAT] [--fo OUTPUT_FORMAT]
               [--rdf_class CLASS] [--prop PROPERTY]
               [--ignore [TERM [TERM ...]]] [--min_ngram N]
               [--no_duplicates [TYPE [TYPE ...]]]
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
                        by the ARPA service. Here 'duplicate' means an
                        individual with the same label. A list of types can be
                        given with this argument. If given, prioritize matches
                        based on it - the first given type will get the
                        highest priority and so on. Note that the response
                        from the service has to include a 'type' variable for
                        this to work.
```

The arguments can also be read from a file using "@" (example arg file "arpa.args"):

`arpa.py @arpa.args`
