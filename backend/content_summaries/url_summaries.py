## imports
import os
import nltk
import re
import string
import gensim
import numpy as np
from nltk.corpus import stopwords
from gutenbergpy import textget
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from gensim import corpora
from gensim.models import LdaModel
from gensim.models.coherencemodel import CoherenceModel
import pyLDAvis
import pyLDAvis.gensim_models as gensimvisualize
import requests
from bs4 import BeautifulSoup
import requests
from bs4 import BeautifulSoup

## download ntlk resources
nltk.download("punkt")
nltk.download('wordnet')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
nltk.download("punkt_tab")
nltk.download("averaged_perceptron_tagger_eng")

# load WordNet POS tags for lemmatization
def wordnet_pos_tags(treebank_tag):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN

# prepocessing pipeline to clean and prepare text for topic modeling, including:
# strip header, lowercase, remove punctuation, tokenize, remove stopword, lemmatize
def txt_preprocess_pipeline(text):
    working_txt = text
    main_txt = textget.strip_headers(working_txt.encode('utf-8')).decode('utf-8')
    main_txt = re.sub(r'end of the project gutenberg', '', main_txt, flags=re.IGNORECASE)
    standard_txt = main_txt.lower()
    clean_txt = re.sub(r'\n', ' ', standard_txt)
    clean_txt = re.sub(r'\s+', ' ', clean_txt)
    clean_txt = clean_txt.strip()
    tokens = word_tokenize(clean_txt)
    filtered_tokens_alpha = [word for word in tokens if word.isalpha() and not re.match(r'\d+', word)]
    stop_words = set(stopwords.words('english'))
    filtered_tokens_stopwords = [word for word in filtered_tokens_alpha if word not in stop_words]
    lemmatizer = WordNetLemmatizer()
    pos_tags = nltk.pos_tag(filtered_tokens_stopwords)
    lemmatized_tokens = [lemmatizer.lemmatize(word, wordnet_pos_tags(tag)) for word, tag in pos_tags]
    return lemmatized_tokens

# take long block of text, use LDA to get 3 main topics
def get_topics(text):
    processed_text = txt_preprocess_pipeline(text)
    dictionary = corpora.Dictionary([processed_text])
    corpus = [dictionary.doc2bow(processed_text)]
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=10,
        random_state=13,
        passes=10
    )
    topics = []
    for idx, topic in lda_model.print_topics(-1):
        topic_words = re.findall(r'\"(.*?)\"', topic)
        # if the same word is in topics already, skip it
        if topic_words[0] not in topics:
            topics.append(' '.join(topic_words[:1]))

        # if topic_words[:1] not in topics:
        #     topics.append(' '.join(topic_words[:1]))
    return topics

# simple function to print the text from a url, using requests and BeautifulSoup to scrape the page content and extract the text
def get_url_text(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        page_text = soup.get_text(separator='\n', strip=True)
        return page_text
    except requests.exceptions.RequestException as e:
        print("Can't access this URL!")
        print(f"An error occurred: {e}")
        return None
    
def top_3_topics_from_url(url):
    url_text = get_url_text(url)
    if url_text:
        topics = get_topics(url_text)
        return topics
    else:
        return None
    
if __name__ == "__main__":
    url = "https://litfl.com/ct-case-103/"  
    print(top_3_topics_from_url(url))