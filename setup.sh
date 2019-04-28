#!/usr/bin/env bash

{
    python -V
    PY=python
} || {
    PY=python3

}

{
    pip -V
    PIP=pip
} || {
    PIP=pip3

}

${PIP} install -r requirements.txt

${PY} -m spacy download en_core_web_sm

${PY} -c "
import nltk
nltk.download('vader_lexicon')
"