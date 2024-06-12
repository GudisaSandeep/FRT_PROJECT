import os
from flask import Flask, render_template, request, send_from_directory, url_for
from azure.ai.textanalytics import TextAnalyticsClient
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.core.credentials import AzureKeyCredential
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioConfig
from azure.core.exceptions import HttpResponseError
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
app = Flask(__name__)

# Azure Text Analytics service credentials
text_api_key = "ec5bf3219a7c434ca4d67a70f8c50a60"
text_endpoint = "https://textclassification1413.cognitiveservices.azure.com/"
text_credential = AzureKeyCredential(text_api_key)
text_analytics_client = TextAnalyticsClient(endpoint=text_endpoint, credential=text_credential)

# Azure Computer Vision service credentials
vision_api_key = "da08e90a4f6045a8abcfedf511efb393"
vision_endpoint = "https://resource1413.cognitiveservices.azure.com/"
vision_credential = AzureKeyCredential(vision_api_key)
vision_client = ComputerVisionClient(vision_endpoint, vision_credential)

# Azure Speech service credentials
speech_subscription_key = "1b028a3218994bf8a96189e8a63f2416"
speech_region = "centralindia"
speech_config = SpeechConfig(subscription=speech_subscription_key, region=speech_region)

subscription_key = '35d2e9121807462b83c5777f2dc1d503'
search_url = "https://api.bing.microsoft.com/v7.0/search"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/resume')
def resume():
    return render_template('resume.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/review')
def review():
    return render_template('index3.html')
def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text()


@app.route('/feedback')
def feedback():
    return render_template('index3.html')
def search_bar():
    return render_template('index.html')
@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query', '')
    if query.strip() != '':
        headers = {"Ocp-Apim-Subscription-Key": subscription_key}
        params = {"q": query, "textDecorations": True, "textFormat": "HTML"}
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        search_results = response.json()
        return render_template('search_results.html', search_results=search_results)
    else:
        return jsonify({})
@app.route('/analyze', methods=['POST'])
def analyze():
    text = request.form.get('text', '')
    image = request.files.get('image')

    # Analyze text feedback
    sentiment = "Unknown"
    language = "Unknown"
    key_phrases = "None"
    entities = "None"
    if text:
        try:
            sentiment_response = text_analytics_client.analyze_sentiment(documents=[text])[0]
            sentiment = sentiment_response.sentiment

            language_response = text_analytics_client.detect_language(documents=[text])[0]
            language = language_response.primary_language.name

            key_phrases_response = text_analytics_client.extract_key_phrases(documents=[text])[0]
            key_phrases = ", ".join(key_phrases_response.key_phrases)

            entities_response = text_analytics_client.recognize_entities(documents=[text])[0]
            entities = ", ".join([entity.text for entity in entities_response.entities])
        except HttpResponseError as e:
            print(f"Text analytics error: {e}")

    # Analyze image (extract text)
    image_text = ""
    if image:
        try:
            image_bytes = image.read()
            image_text_results = vision_client.read_in_stream(image_bytes, language="en")
            operation_location_remote = image_text_results.headers["Operation-Location"]
            operation_id = operation_location_remote.split("/")[-1]

            # Retrieve the results
            image_text_results = vision_client.get_read_result(operation_id)
            if image_text_results.status == 'succeeded':
                for result in image_text_results.analyze_result.read_results:
                    for line in result.lines:
                        image_text += line.text + " "
        except HttpResponseError as e:
            image_text = "Unable to analyze text from the image."
            print(f"Vision analysis error: {e}")

    # Synthesize speech from input text
    if text:
        input_audio_filename = "input_text.wav"
        input_audio_filepath = os.path.join("static", input_audio_filename)
        input_audio_output = AudioConfig(filename=input_audio_filepath)
        input_synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=input_audio_output)
        input_synthesizer.speak_text_async(text).get()

    # Synthesize speech from analysis result
    result_text = f"Sentiment: {sentiment}. Language: {language}. Key Phrases: {key_phrases}. Entities: {entities}. {image_text}"
    result_audio_filename = "result_text.wav"
    result_audio_filepath = os.path.join("static", result_audio_filename)
    result_audio_output = AudioConfig(filename=result_audio_filepath)
    result_synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=result_audio_output)
    result_synthesizer.speak_text_async(result_text).get()

    return render_template('result3.html', 
                           sentiment=sentiment, 
                           language=language, 
                           key_phrases=key_phrases, 
                           entities=entities, 
                           image_text=image_text,
                           input_audio_filename=input_audio_filename,
                           result_audio_filename=result_audio_filename)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)
