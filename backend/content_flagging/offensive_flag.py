#imports
from keras.models import load_model
import os
import joblib
from tensorflow.keras.preprocessing.sequence import pad_sequences
import nltk 
from nltk.corpus import stopwords 
import re
import requests
from bs4 import BeautifulSoup
from keras import layers
import keras
from keras.models import load_model
import os
import joblib
import tensorflow.keras.backend as K

MODEL_PATH = os.path.join(os.path.dirname(__file__), "offensive_model.keras")
model = load_model(MODEL_PATH, compile=False)
tokenizer = joblib.load("backend/content_flagging/tokenizer.sav")
max_length = joblib.load("backend/content_flagging/max_length.sav")

stop_words = set(stopwords.words('english'))
stop_words.add("rt")

LABEL_MAP = {
    0: "HATE_SPEECH",
    1: "OFFENSIVE",
    2: "NEITHER"
}

# remove html entity:
def remove_entity(raw_text):
    entity_regex = r"&[^\s;]+;"
    text = re.sub(entity_regex, "", raw_text)
    return text

# change the user tags
def change_user(raw_text):
    regex = r"@([^ ]+)"
    text = re.sub(regex, "user", raw_text)

    return text

# remove urls
def remove_url(raw_text):
    url_regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    text = re.sub(url_regex, '', raw_text)

    return text

# remove unnecessary symbols
def remove_noise_symbols(raw_text):
    text = raw_text.replace('"', '')
    text = text.replace("'", '')
    text = text.replace("!", '')
    text = text.replace("`", '')
    text = text.replace("..", '')

    return text

# remove stopwords
def remove_stopwords(raw_text):
    tokenize = nltk.word_tokenize(raw_text)
    text = [word for word in tokenize if not word.lower() in stop_words]
    text = " ".join(text)

    return text

## this function in to clean all the dataset by utilizing all the function above
def preprocess(datas):
    clean = []
    # change the @xxx into "user"
    clean = [change_user(text) for text in datas]
    # remove emojis (specifically unicode emojis)
    clean = [remove_entity(text) for text in clean]
    # remove urls
    clean = [remove_url(text) for text in clean]
    # remove trailing stuff
    clean = [remove_noise_symbols(text) for text in clean]

    # for now im not going to remove stopwords, might help improve accuracy 
    # # remove stopwords
    # clean = [remove_stopwords(text) for text in clean]

    return clean

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

def split_into_chunks(text, max_words=40):
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i:i+max_words]))
    return chunks

# use model to predict on new text
def predict_offensive(text):
    clean_text = preprocess([text])[0]
    seq = tokenizer.texts_to_sequences([clean_text])
    padded_seq = pad_sequences(seq, maxlen=max_length)
    pred = model.predict(padded_seq)
    pred_class = pred.argmax(axis=1)[0]
    return LABEL_MAP[pred_class]

def predict_offensive_from_url(url):
    url_text = get_url_text(url)
    if not url_text:
        return None
    chunks = split_into_chunks(url_text)
    results = [predict_offensive(chunk) for chunk in chunks]

    # print the chunks labelled as HATE_SPEECH or OFFENSIVE
    for i, result in enumerate(results):
        if result in ["HATE_SPEECH", "OFFENSIVE"]:
            print(f"Chunk {i}: {result}: {chunks[i]}")

    # if over half of the chunks are flagged, flag the whole text
    if results.count("HATE_SPEECH") + results.count("OFFENSIVE") > len(results) / 2:
        return "FLAGGED"
    else:
        return "CLEAN"
       


if __name__ == "__main__":
    print(predict_offensive_from_url("https://wwf.org.au/blogs/9-interesting-platypus-facts/"))
