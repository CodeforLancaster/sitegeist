#!/usr/bin/env bash
pip3 install -r requirements.txt
python3 -m spacy download en_core_web_sm

python3 -c "
import nltk
nltk.download('vader_lexicon')
"