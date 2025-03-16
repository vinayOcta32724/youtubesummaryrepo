import os
from openai import OpenAI
import requests
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from twilio.rest import Client
from flask import Flask, request, abort


# Set up API keys and credentials
#openai_api_key = os.getenv("OPENAI_API_KEY", "your_openai_api_key")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
brevo_api_key = os.getenv("BREVO_API_KEY")
callback_url = os.getenv("RENDER_CALLBACK_URL")
verify_token =  os.getenv("VERIFY_TOKEN")

# Initialize APIs
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

client = OpenAI(
    api_key=openai_api_key  
)

app = Flask(__name__)

def get_videos_from_channel(channel_id):
    # Fetch the list of videos from the specified channel
    request = youtube.search().list(
        part='snippet',
        channelId=channel_id,
        maxResults=50,
        order='date'
    )
    response = request.execute()
    return response['items']

def get_transcript(video_id):
    # Retrieve the transcript of the video
    try:
      transcript = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({'error': f"An error occurred: {e}"}), 500
    return ' '.join([t['text'] for t in transcript])

def summarize_text(text):
    # Summarize the text using OpenAI's API
    # response = client.completions.create(
    #     model=openai_model,
    #     prompt='Summarize the following text:\n\n' + text,
    #     max_tokens=150
    # )
    # return response.choices[0].text.strip()
    response = client.chat.completions.create(
    model=openai_model,
    messages=[
        {
            "role": "system",
            "content": "You are an AI assistant for summarizing YouTube video transcripts.Your task is to provide a concise summary of the given transcript.",
        },
        {
            "role": "user",
            "content": 'Summarize the following text:\n\n' + text,
        },
    ],
)

    return response.choices[0].message.content

def send_whatsapp_message(to, message):
    # Send the message to the specified WhatsApp number using Twilio's API
    out = twilio_client.messages.create(
        from_='whatsapp:+14155238886',  # Twilio sandbox number
        to='whatsapp:' + to,
        body=message
    )
    
    print(out)

@app.route('/')
def index():
    return "YouTube Summary to WhatsApp App is running!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verification challenge
        hub_mode = request.args.get('hub.mode')
        hub_challenge = request.args.get('hub.challenge')
        hub_verify_token = request.args.get('hub.verify_token')
        if hub_mode == 'subscribe' and hub_verify_token == verify_token:
            return hub_challenge, 200
        else:
            abort(403)
    elif request.method == 'POST':
        # Handle notification
        data = request.get_json()
        for entry in data['feed']['entry']:
            video_id = entry['yt:videoId']
            video_url = f'https://www.youtube.com/watch?v={video_id}'
            video_title = entry['title']

            # Get the transcript and summarize it
            transcript = get_transcript(video_id)
            summary = summarize_text(transcript)

            # Send the summary to WhatsApp
            message = f'Video: {video_title}\n\n URL: {video_url}\n\n Summary: {summary}'
            #send_whatsapp_message('+918008266369', message)
            send_email_via_brevo("vinay.32724@gmail.com", "Summary for "+ video_title, message)

        return '', 200

def subscribe_to_channel(channel_id, callback_url, verify_token):
    hub_url = "https://pubsubhubbub.appspot.com/subscribe"
    topic_url = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"
    data = {
        "hub.mode": "subscribe",
        "hub.topic": topic_url,
        "hub.callback": callback_url,
        "hub.verify": "async",
        "hub.verify_token": verify_token,
    }
    response = requests.post(hub_url, data=data)
    if response.status_code == 202:
        print("Subscription request sent successfully.")
    else:
        print("Failed to send subscription request.")
        print(response.text)

def process_videos(channel_id):
    videos = get_videos_from_channel(channel_id)
    for video in videos:
        video_id = video['id']['videoId']
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        video_title = video['snippet']['title']

        # Get the transcript and summarize it
        transcript = get_transcript(video_id)
        summary = summarize_text(transcript)

        # Send the summary to WhatsApp
        message = f'Video: {video_title}\nURL: {video_url}\nSummary: {summary}'
        send_whatsapp_message('+918008266369', message)

def send_email_via_brevo(recipient_email, subject, body):
    
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": brevo_api_key,
        "content-type": "application/json"
    }
    payload = {
        "sender": {"email": "videosummary369@gmail.com"},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "htmlContent": body
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print("Email sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send email: {e}")

# Example usage
# send_email_via_brevo('recipient@example.com', 'Test Subject', 'This is a test email.', 'your_email@example.com', 'your_brevo_api_key')

if __name__ == '__main__':
    channel_ids = ["UCwKB_00dPL3x5XmHF9IJCrg", "UCqW8jxh4tH1Z1sWPbkGWL4g", "UC7kCeZ53sli_9XwuQeFxLqw","UCdc6ObxhdQ8eZIFquU2xolA"] #parkev,akshat, tickersymbolyou, sahil
    for channel_id in channel_ids:
        subscribe_to_channel(channel_id, callback_url, verify_token)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
