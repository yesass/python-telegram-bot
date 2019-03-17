import logging
import telegram
from telegram.error import NetworkError, Unauthorized
from telegram.ext import Updater
from time import sleep
import subprocess
import time
import wave
import http.client, urllib.request, urllib.parse, urllib.error, base64
import json

counter = 0

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    print("""
    Importing the Speech SDK for Python failed.
    Refer to
    https://docs.microsoft.com/azure/cognitive-services/speech-service/quickstart-python for
    installation instructions.
    """)
    import sys
    sys.exit(1)

speech_key, service_region = "", "eastasia"
update_id = None
headers = {
    'Content-Type': 'application/json',
    'Ocp-Apim-Subscription-Key': '',
}
params = urllib.parse.urlencode({
})

def giveScore(weatherfilename):
    restext = speech_recognize_once_from_file(weatherfilename)
    body = {
      "documents": [
            {
                "language": "en",
                "id": "1",
                "text": restext
            }
        ]
    }

    try:
        conn = http.client.HTTPSConnection('eastasia.api.cognitive.microsoft.com')
        conn.request("POST", "/text/analytics/v2.0/sentiment?%s" % params, str(body), headers)
        response = conn.getresponse()
        data = response.read()
        data = json.loads(data)
        score = float(data['documents'][0]['score'])
        scores.append(score)
        # print(score)
        conn.close()
    except Exception as e:
        print("error")
    return restext, score

def speech_recognize_once_from_file(weatherfilename):
    """performs one-shot speech recognition with input from an audio file"""
    # <SpeechRecognitionWithFile>
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioConfig(filename=weatherfilename)
    # Creates a speech recognizer using a file as audio input.
    # The default language is "en-us".
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    # Starts speech recognition, and returns after a single utterance is recognized. The end of a
    # single utterance is determined by listening for silence at the end or until a maximum of 15
    # seconds of audio is processed. It returns the recognition text as result.
    # Note: Since recognize_once() returns only a single utterance, it is suitable only for single
    # shot recognition like command or query.
    # For long-running multi-utterance recognition, use start_continuous_recognition() instead.
    result = speech_recognizer.recognize_once()

    # Check the result
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        result_text = result.text
        # print(result_text)
        # print("Recognized: {}".format(result.text))
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(result.no_match_details))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
    # </SpeechRecognitionWithFile>
    return result_text

def main():    
    """Run the bot."""
    global update_id
    # Telegram Bot Authorization Token
    bot = telegram.Bot('')

    # get the first pending update_id, this is so we can skip over it in case
    # we get an "Unauthorized" exception.
    try:
        update_id = bot.get_updates()[0].update_id
    except IndexError:
        update_id = None

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    while True:
        try:
            echo(bot)
        except NetworkError:
            sleep(1)
        except Unauthorized:
            # The user has removed or blocked the bot.
            update_id += 1

def echo(bot):
    """Echo the message the user sent."""
    global update_id
    global counter
    # Request updates after the last update_id
    for update in bot.get_updates(offset=update_id, timeout=10):
        update_id = update.update_id + 1

        if update.message.voice:
            file = bot.getFile(update.message.voice.file_id)
            print ("file_id: " + str(update.message.voice.file_id))
            file.download('voice.ogg')

            src_filename = 'voice.ogg'
            dest_filename = 'voice_00' + str(counter) + '.wav'
            counter += 1

            process = subprocess.run(['ffmpeg', '-i', src_filename, dest_filename])
            if process.returncode != 0:
                raise Exception("Something went wrong")

            text, score = giveScore(dest_filename)
            update.message.reply_text(str(text) + ' ' + str(score))

if __name__ == '__main__':
    main()
