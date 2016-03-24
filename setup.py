import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="arpa_linker",
    version="0.3.0",
    author="Erkki Heino",
    description="Tool for linking rdf datasets to other datasets using ARPA",
    license="MIT",
    keywords="rdf",
    url="http://semanticcomputing.github.io/python-arpa-linker/",
    long_description=read('README.md'),
    packages=['arpa_linker'],
    install_requires=[
        'rdflib >= 4.2.0',
        'requests >= 2.7.0'
    ],
)
