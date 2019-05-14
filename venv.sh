#!/usr/bin/env bash

sudo apt-get install virtualenv

if [[ ! -d "venv-sitegeist" ]];
then
    virtualenv venv-sitegeist --python=python3.6
    source ./venv-sitegeist/bin/activate
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

else
    source ./venv-sitegeist/bin/activate

fi