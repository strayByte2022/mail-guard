# ml_utils.py
import re
import string
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

stop_words = set(stopwords.words("english"))
stemmer = PorterStemmer()

def clean_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"<[^>]+>", " ", s)          # drop HTML tags
    s = re.sub(r"[^a-z0-9\s]", " ", s)      # keep alphanumerics
    toks = [w for w in s.split() if len(w) > 2]
    toks = [stemmer.stem(w) for w in toks if w not in stop_words]
    return " ".join(toks)

def clean_texts(texts):
    return [clean_text(t) for t in texts]
