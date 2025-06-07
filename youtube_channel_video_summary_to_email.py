import os
from openai import OpenAI
import requests
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from twilio.rest import Client
from flask import Flask, request, abort
from datetime import datetime, timedelta
import time
import logging
from logging.handlers import TimedRotatingFileHandler

# Set up logging
log_file = os.path.join(os.path.dirname(__file__), 'youtube_summary.log')
logger = logging.getLogger('YoutubeSummary')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=30)
handler.setFormatter(formatter)
logger.addHandler(handler)


# Set up API keys and credentials
openai_api_key ='API_KEY_OPENAI'
openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
YOUTUBE_API_KEY = 'API_KEY_YT'
brevo_api_key = "API_KEY_BREVO"
receipient_email = "RECE_EMAIL@gmail.com"

# Initialize APIs
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
#twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

client = OpenAI(
    api_key=openai_api_key  
)

def get_videos_from_channel(channel_id, days):
    # Calculate the date 'days' ago from today
    date_from = (datetime.utcnow() - timedelta(days=days)).isoformat("T") + "Z"

    logger.info(f"Fetching videos for channel {channel_id} from {date_from}")
    try:
        # Fetch the list of videos from the specified channel
        request = youtube.search().list(
            part='snippet',
            channelId=channel_id,
            maxResults=50,
            order='date',
            publishedAfter=date_from
        )
        response = request.execute()
        video_count = len(response['items'])
        logger.info(f"Successfully fetched {video_count} videos from channel {channel_id}")
        return response['items']
    except Exception as e:
        logger.error(f"Failed to fetch videos from channel {channel_id}: {str(e)}")
        return []

def get_transcript(video_id, max_retries=2, delay_seconds=5):
    # Retrieve the transcript of the video with retries
    logger.info(f"Attempting to get transcript for video {video_id}")
    for attempt in range(max_retries + 1):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = ' '.join([t['text'] for t in transcript])
            logger.info(f"Successfully retrieved transcript for video {video_id}")
            return transcript_text
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed for video {video_id}: {str(e)}")
                logger.info(f"Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
                # Increase delay for next retry
                delay_seconds *= 2
            else:
                logger.error(f"All {max_retries + 1} attempts failed for video {video_id}: {str(e)}")
                return ""

def summarize_text(text):
    # Summarize the text using OpenAI's API
    if not text:
        logger.warning("Received empty text for summarization")
        return "Summary not available - no transcript provided"
    
    logger.info("Attempting to summarize text using OpenAI API")
    try:
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
        logger.info("Successfully generated summary using OpenAI API")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Failed to summarize text: {str(e)}")
        return "Summary not available due to an error."


def process_videos(channel_id, channel_name, days):
    logger.info(f"Starting video processing for channel {channel_name} ({channel_id})")
    videos = get_videos_from_channel(channel_id, days)
    
    if not videos:
        logger.warning(f"No videos found for channel {channel_name}")
        return
        
    logger.info(f"Processing {len(videos)} videos from channel {channel_name}")
    for video in videos:
        video_id = video['id']['videoId']
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        video_title = video['snippet']['title']
        
        logger.info(f"Processing video: {video_title} ({video_id})")
        # Delay by 5 seconds to avoid rate limiting
        time.sleep(5)
        
        # Get the transcript and summarize it
        transcript = get_transcript(video_id)
        if transcript:
            summary = summarize_text(transcript)
            message = f'Video: {video_title}\n\n   URL: {video_url}\n\n   Summary: {summary}'
        else:
            logger.warning(f"No transcript available for video {video_id}")
            summary = "Summary not available due to an error in transcript API"
            message = f'Video: {video_title}\n\n URL: {video_url}\n\n Summary: {summary}'
            
        # Send the email with the summary
        send_email_via_brevo(receipient_email, "Summary for "+ video_title + " from "+channel_name, message)
    
    logger.info(f"Completed processing videos for channel {channel_name}")

def send_email_via_brevo(recipient_email, subject, body):
    logger.info(f"Attempting to send email to {recipient_email}: {subject}")
    
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
        logger.info(f"Successfully sent email to {recipient_email}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
 

if __name__ == '__main__':
    channel_ids = ["UCwKB_00dPL3x5XmHF9IJCrg", "UCqW8jxh4tH1Z1sWPbkGWL4g", "UC7kCeZ53sli_9XwuQeFxLqw","UCdc6ObxhdQ8eZIFquU2xolA","UCJwKCyEIFHwUOPQQ-4kC1Zw","UC2MU9phoTYy5sigZCkrvwiw","UCdUEJABvX8XKu3HyDSczqhA","UCESh5daDcPqvG0QhbSdzIzw","UCyqlbzLoYtpqDXwRI9Yh5LA"] 
    channel_name =["parkev","akshat", "tickersymbolyou", "sahil", "Tom Nash", "Rahul","shahank","Millionarie Secrets", "Business with Brian"]
    #channel_ids and channel_name should be same length
    # do the check here
    for i in range(len(channel_ids)):  
            process_videos(channel_ids[i],channel_name[i],1)
    
