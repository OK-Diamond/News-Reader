'''Gets the latest news from the BBC and summarises it using OpenAI's ChatGPT.'''

from pathlib import Path
from dataclasses import dataclass
from time import sleep
from bs4 import BeautifulSoup as bsoup # pip install bs4 (for webscaper), pip install lxml (for xml reader addon)
from playsound import playsound # pip install playsound - Used to play audio
import openai # pip install openai - Used to generate text and speech
import requests # Used to get the xml data from the BBC website
import pyttsx3 # pip install pyttsx3
import constants

class AIChat:
    '''Sends reqests to the OpenAI API and cleans responses.'''
    def __init__(self, client: openai.OpenAI) -> None:
        # Example OpenAI Python library request
        self.client = client
        self.model = "gpt-3.5-turbo"
        self.temperature = 0.5
        self.num_of_responses = 1
        self.inputs = [{
            "role": "system", 
            "content":
                """The user will input text taken from a BBC News article and you will summarise it in one to three sentences.
                The article may contain biased language, so you should attempt to rephrase it to be more politically neutral.
                You are delivering a daily news briefing to the user, so you should provide a summary of the article's main points without mentioning the article directly."""
        }]

    def run_ai(self):
        '''Sends and API reqest with stored data.'''
        return self.client.chat.completions.create(
            model = self.model,
            messages = self.inputs,
            temperature = self.temperature,
            n = self.num_of_responses,
        )
    def add_input(self, inputs: dict) -> None:
        '''Adds an extra line to the input.\n
        Example input: {"role": "user", "content": """Hello!"""}'''
        self.inputs.append(inputs)


@dataclass
class News:
    '''Manages webscraping news information.'''
    def __init__(self, url: str) -> None:
        self.url = url

    def _get_soup(self, url: str, features: str) -> bsoup:
        '''Scrapes data from an xml url.'''
        response = requests.get(url, timeout=10)
        data = bsoup(response.text, features)
        return data

    def _get_body(self, url: str, features: str, text_class: str) -> str:
        '''Gets the body data from the given url.'''
        soup = self._get_soup(url, features)
        story = soup.find(text_class).get_text()
        return story

class BBCNews (News):
    '''Manages webscraping news information from the BBC.'''
    def __init__(self) -> None:
        super().__init__("http://feeds.bbci.co.uk/news/rss.xml")

    def get_headlines(self) -> list[str]:
        '''Retrieves the current headlines from the given url. Returns [title, description, body].'''
        soup = self._get_soup(self.url, "xml") # Request and parse xml
        articles = list(soup.find_all('item')) # Isolate the articles from the rest of the page info
        found_article = False
        counter = 0
        while not found_article:
            try:
                body = self._get_body(articles[counter].link.text, "xml", "article")
                found_article = True
            except AttributeError:
                print("Article not found, trying next article.")
                counter += 1
        return articles[0].title.text, articles[0].description.text, body


class TTSOld:
    '''Manages text-to-speech (tts). This is the older version that uses the pyttsx3 library.'''
    def __init__(self) -> None:
         # object creation
        self.engine = pyttsx3.init()
         # Changes voice rate
        self.engine.setProperty('rate', 125)
         # Changes volume level, between 0 and 1
        self.engine.setProperty('volume', 1.0)
         # Changes voices. 0 = terrible generic voice, 1 = passable american voice.
        self.engine.setProperty('voice', self.engine.getProperty('voices')[1].id)

    def say_text(self, text: str) -> None:
        '''Reads out the given text. Make sure your volume is on!'''
        self.engine.say(text)
        self.engine.runAndWait()
        self.engine.stop()

class TTS:
    '''Manages text-to-speech (tts). New version that uses the OpenAI's tts.'''
    def __init__(self, client: openai.OpenAI, filename: str = "news") -> None:
        self.client = client
        self.path = Path(__file__).parent / f"{filename}.mp3"

    def create_audio(self, text: str) -> None:
        '''Creates an audio file from the given text and saves it to the path.'''
        response = self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        response.stream_to_file(self.path)

    def play_audio(self) -> None:
        '''Plays the audio file saved at the path.'''
        playsound(self.path.name)


def main() -> None:
    '''Main function'''
     # Create OpenAI object
    client = openai.OpenAI(
        api_key = constants.OPENAI_API_KEY
    )

     # Get news info
    news = BBCNews()
    title, description, body = news.get_headlines()
    #print("Title:", title)
    #print("Description:", description)
    #print("Body:", body)
    #print("\n\n\n")

     # Pass into ChatGPT
    ai_chat = AIChat(client)
    ai_chat.add_input({"role": "user", "content": f"Article Title: {title}"})
    ai_chat.add_input({"role": "user", "content": f"Article Description: {description}"})
    ai_chat.add_input({"role": "user", "content": f"Article Body: {body}"})
    response = ai_chat.run_ai()

     # Display result
    for i in response.choices:
        print(i.message.content)

     # Read out result using text-to-speech
    tts = TTS(client)
    tts.create_audio(response.choices[0].message.content)
    sleep(0.5) # Allow time for the file to be created
    tts.play_audio()


if __name__ == "__main__":
    main()
