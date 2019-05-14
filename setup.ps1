
.\venv-sitegeist\Scripts\activate


Try {
    python3 -V
    python3 -m spacy download en_core_web_sm
    python -c "import nltk
nltk.download('vader_lexicon')"
} Catch {
    python -V
    python -m spacy download en_core_web_sm
    python -c "import nltk
nltk.download('vader_lexicon')"
}

