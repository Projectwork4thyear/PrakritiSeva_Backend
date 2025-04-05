import spacy
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download('stopwords', quiet=True)
nltk.download('punkt_tab', quiet=True)
nlp = spacy.load("en_core_web_sm")

def extract_keywords(text):
    doc = nlp(text)
    stop_words = set(stopwords.words('english'))
    keywords = set()

    for chunk in doc.noun_chunks:
        keyword = chunk.text.lower()
        if keyword not in stop_words:
            keywords.add(keyword)

    for ent in doc.ents:
        keywords.add(ent.text.lower())

    words = word_tokenize(text)
    filtered_words = [word.lower() for word in words if word.isalpha() and word.lower() not in stop_words]
    keywords.update(filtered_words)

    return list(keywords)
