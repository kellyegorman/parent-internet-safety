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

# thresholds: weighted score per chunk: HATE_SPEECH=2, OFFENSIVE=1, NEITHER=0
# final score = total_weighted_points / total_possible_points
# so page full of hate speech scores 1.0, all offensive scores 0.5,
# all clean scores 0.0. Thresholds below control which tier is triggered.

SEVERE_THRESHOLD   = 0.50  # high density of hate speech (originally 0.8)
MODERATE_THRESHOLD = 0.20  # mix of offensive/hate content (originally 0.5)
WATCH_THRESHOLD    = 0.05  # low but non-trivial signal (originally 0.2)

# only judge pages with at least this many chunks (was 5 before)
MIN_CHUNKS = 3

# make chunk size larger, give the model more context, less false positives
CHUNK_SIZE = 80  


# process text
def remove_entity(raw_text):
    return re.sub(r"&[^\s;]+;", "", raw_text)

def change_user(raw_text):
    return re.sub(r"@([^ ]+)", "user", raw_text)

def remove_url(raw_text):
    url_regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»""'']))"
    return re.sub(url_regex, '', raw_text)

def remove_noise_symbols(raw_text):
    text = raw_text.replace('"', '')
    text = text.replace("'", '')
    text = text.replace("!", '')
    text = text.replace("`", '')
    text = text.replace("..", '')
    return text

def preprocess(datas):
    clean = [change_user(text) for text in datas]
    clean = [remove_entity(text) for text in clean]
    clean = [remove_url(text) for text in clean]
    clean = [remove_noise_symbols(text) for text in clean]
    return clean


# get URL
def get_url_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # remove noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        return soup.get_text(separator='\n', strip=True)
    except requests.exceptions.RequestException as e:
        print(f"Can't access this URL: {e}")
        return None


# chunk

def split_into_chunks(text, max_words=CHUNK_SIZE):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]


#  predict each chunk

def predict_offensive(text):
    clean_text = preprocess([text])[0]
    seq = tokenizer.texts_to_sequences([clean_text])
    padded_seq = pad_sequences(seq, maxlen=max_length)
    pred = model.predict(padded_seq, verbose=0)
    pred_class = pred.argmax(axis=1)[0]
    return LABEL_MAP[pred_class]


# main feature

def predict_offensive_from_url(url):
    """
    Returns one of:
      "urgent"   — high concentration of hate speech
      "moderate" — meaningful offensive/hate content
      "watch"    — low but present signal worth monitoring
      "clean"    — no significant offensive content detected
      "insufficient_data" — page too short to judge reliably
      None       — page could not be fetched
    """
    url_text = get_url_text(url)
    if not url_text:
        return None

    chunks = split_into_chunks(url_text)

    if len(chunks) < MIN_CHUNKS:
        return "insufficient_data"

    results = [predict_offensive(chunk) for chunk in chunks]

    # Weighted scoring: hate speech counts double vs. merely offensive
    # This prevents a page with one hate chunk and many offensive chunks from being downgraded unfairly, and vice versa.
    hate_count      = results.count("HATE_SPEECH")
    offensive_count = results.count("OFFENSIVE")
    total_chunks    = len(results)

    weighted_score = (hate_count * 2 + offensive_count * 1) / (total_chunks * 2)

    # Log flagged chunks for debugging
    for i, result in enumerate(results):
        if result in ("HATE_SPEECH", "OFFENSIVE"):
            print(f"  Chunk {i} [{result}]: {chunks[i][:80]}…")

    print(f"  Score: {weighted_score:.3f} | hate={hate_count} offensive={offensive_count} total={total_chunks}")

    if weighted_score >= SEVERE_THRESHOLD:
        return "urgent"
    elif weighted_score >= MODERATE_THRESHOLD:
        return "moderate"
    elif weighted_score >= WATCH_THRESHOLD:
        return "watch"
    else:
        return "clean"


if __name__ == "__main__":
    url = "https://wwf.org.au/blogs/9-interesting-platypus-facts/"
    result = predict_offensive_from_url(url)
    print(f"\nVerdict: {result}")