from better_profanity import profanity
import requests
from bs4 import BeautifulSoup

profanity.load_censor_words()

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

text = get_url_text("https://www.refinery29.com/en-gb/best-am-i-the-asshole-reddit-stories")

# print(profanity.censor(text)) 
print(profanity.contains_profanity(text))   

# print the words in block of text that cause contains_profanity to return true
def get_offensive_words(text):
    words = text.split()
    offensive_words = [word for word in words if profanity.contains_profanity(word)]
    return offensive_words
print(get_offensive_words(text))
