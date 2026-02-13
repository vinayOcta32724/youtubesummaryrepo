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
import xml.etree.ElementTree as ET
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Set up logging
log_file = os.path.join(os.path.dirname(__file__), 'youtube_summary.log')
logger = logging.getLogger('YoutubeSummary')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=30)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Set up API keys and credentials
#openai_api_key = os.getenv("OPENAI_API_KEY", "your_openai_api_key")
openai_api_key ='xxxxx
openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

YOUTUBE_API_KEY = 'xxxxx' # Replace with your YouTube transcript io  API key
YOUTUBE_SEARCH_API_KEY = 'xxxxx' # Replace with your YouTube searchapi.io API key
YTIO_TRANSCRIPT_API_KEY = 'xxxxxx'

# Resend API Configuration (3,000 emails/month free)
RESEND_API_KEY = "xxxxx"  # Get from resend.com - replace this - This is created using vinay.32724@gmail.com
FROM_EMAIL = "xxxxx"     # Replace with your verified domain or use resend domain

# Initialize APIs
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
 

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
import requests
import time
import requests

def fetch_youtube_transcript_search_api(video_id: str, api_key: str) -> list:
    """
    Fetches the transcript for a given YouTube video ID using searchapi.io.
    Returns a list of transcript segments.
    """
    url = "https://www.searchapi.io/api/v1/search"
    params = {
        "engine": "youtube_transcripts",
        "video_id": video_id,
        "api_key": api_key
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for bad responses
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for video {video_id}: {str(e)}")
        return None
    if response.status_code == 200:
        res = response.json()
        data = res.get('transcripts', None)
        if data and len(data) > 0:
            transcript_parts = []
            for item in data:
                if 'text' in item:
                    transcript_parts.append(item['text'])
            transcript = ' '.join(transcript_parts)
            logger.info(f"Successfully extracted transcript ({len(transcript)} characters)")
            return transcript
        else:
            logger.warning(f"No data received from API for video {video_id}")
            return None
    else:
        logger.error(f"API Error for video {video_id}: {response.status_code}")
        return None
    response.raise_for_status()
    data = response.json()
    return data.get("transcripts", [])

# Example usage:
# transcript = fetch_youtube_transcript("0e3GPea1Tyg", "nJhxXk61xWzvS96vPfzEzSED")
# print(transcript)   

def get_transcript_from_ytio(video_id: str, max_retries: int = 2, delay_seconds: int = 2) -> Optional[str]:
    """
    Get transcript for a YouTube video using youtube-transcript.io API and extract from tracks[en]->transcript
    
    Args:
        video_id (str): YouTube video ID
        max_retries (int): Number of retries for API call in case of failure
        delay_seconds (int): Delay in seconds between retries
        
    Returns:
        Optional[str]: Transcript text or None if error
    """
    api_url = "https://www.youtube-transcript.io/api/transcripts"
    api_token = YTIO_TRANSCRIPT_API_KEY
    headers = {
        "Authorization": f"Basic {api_token}",
        "Content-Type": "application/json"
    }
    
    logger.info(f"Attempting to get transcript from youtube-transcript.io for video {video_id}")
    for attempt in range(max_retries):
        try:
            # Make API request
            payload = {"ids": [video_id]}
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 0:
                    transcript_data = data[0]
                    
                    # Check what tracks contains
                    if 'tracks' in transcript_data:
                        tracks = transcript_data['tracks']
                        
                        # Check for tracks[en]->transcript format
                        if isinstance(tracks, dict) and 'en' in tracks and 'transcript' in tracks['en']:
                            transcript = tracks['en']['transcript']
                            logger.info(f"Successfully extracted transcript from tracks[en]->transcript ({len(transcript)} characters)")
                            return transcript
                        
                        # Handle list format where tracks is a list with language='en'
                        elif isinstance(tracks, list):
                            for track in tracks:
                                if isinstance(track, dict) and track.get('language') == 'en' and 'transcript' in track:
                                    segments = track['transcript']
                                    transcript_parts = []
                                    for segment in segments:
                                        if 'text' in segment:
                                            transcript_parts.append(segment['text'])
                                    
                                    if transcript_parts:
                                        transcript = ' '.join(transcript_parts)
                                        logger.info(f"Successfully extracted transcript from tracks ({len(transcript)} characters)")
                                        return transcript
                    
                    # Fallback: Check for segments format (common with youtube-transcript.io)
                    if 'segments' in transcript_data:
                        segments = transcript_data['segments']
                        transcript_parts = []
                        for segment in segments:
                            if 'text' in segment:
                                transcript_parts.append(segment['text'])
                        
                        if transcript_parts:
                            transcript = ' '.join(transcript_parts)
                            logger.info(f"Successfully extracted transcript from segments ({len(transcript)} characters)")
                            return transcript
                    
                    logger.warning(f"No transcript found in expected formats for video {video_id}")
                    return None
                else:
                    logger.warning(f"No data received from API for video {video_id}")
                    return None
            else:
                logger.error(f"API Error for video {video_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting transcript from youtube-transcript.io for video {video_id}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying... ({attempt + 1}/{max_retries})")
                time.sleep(delay_seconds)  # Delay before retrying
            else:
                logger.error(f"Max retries reached for video {video_id}.")
                return None

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

  

def send_email_via_resend(recipient_email, subject, body):
    """Send email using Resend API (3,000 emails/month free)"""
    logger.info(f"Attempting to send email via Resend API to {recipient_email}: {subject}")
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": FROM_EMAIL,
            "to": [recipient_email],
            "subject": subject,
            "text": body
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Successfully sent email via Resend API to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send email via Resend API to {recipient_email}: {str(e)}")

def process_videos(channel_id, channel_name, days):
    logger.info(f"Starting video processing for channel {channel_name} ({channel_id})")
    videos = get_videos_from_channel(channel_id, days)
    if not videos:
        logger.warning(f"No videos found for channel {channel_name}")
        return
    logger.info(f"Processing {len(videos)} videos from channel {channel_name}")
    for video in videos:
        video_id = video.get('id', {}).get('videoId', None)
        video_url = f'https://www.youtube.com/watch?v={video_id}' if video_id else 'N/A'
        video_title = video.get('snippet', {}).get('title', 'Untitled Video')
        logger.info(f"Processing video: {video_title} ({video_id})" if video_id else f"Processing video: {video_title} (ID not available)")
        
        transcript = get_transcript_from_ytio(video_id) if video_id else None
        if not transcript and video_id:
            transcript = fetch_youtube_transcript_search_api(video_id,YOUTUBE_SEARCH_API_KEY)

        if transcript:
            summary = summarize_text(transcript)
            message = f'Video: {video_title}\n\n   URL: {video_url}\n\n   Summary: {summary}'
        else:
            logger.warning(f"No transcript available for video {video_id} from both APIs" if video_id else "No transcript available for untitled video")
            summary = "Summary not available due to an error in transcript APIs"
            message = f'Video: {video_title}\n\n URL: {video_url}\n\n Summary: {summary}'
        
        send_email_via_resend("vinay.32724@gmail.com", "Summary for "+ video_title + " from "+channel_name, message)
        time.sleep(2)  # Delay of 5 seconds between transcript calls
    logger.info(f"Completed processing videos for channel {channel_name}")

if __name__ == '__main__':
    channel_ids = ["UCwKB_00dPL3x5XmHF9IJCrg","UCqW8jxh4tH1Z1sWPbkGWL4g", "UC7kCeZ53sli_9XwuQeFxLqw","UCdc6ObxhdQ8eZIFquU2xolA","UCJwKCyEIFHwUOPQQ-4kC1Zw","UC2MU9phoTYy5sigZCkrvwiw","UCdUEJABvX8XKu3HyDSczqhA","UCESh5daDcPqvG0QhbSdzIzw","UCyqlbzLoYtpqDXwRI9Yh5LA","UCtnItzU7q_bA1eoEBjqcVrw","UCxdWHEhEPiYhCADMrn4PdhQ","UCC7xhD0o7FBHdKXZxMRFspQ"]
    channel_name = ["parkev","akshat", "tickersymbolyou", "sahil", "Tom Nash", "Rahul","shahank","Millionarie Secrets", "Business with Brian","ShankarNath","Fintek","MarkRoussinCPA"]
    for i in range(len(channel_ids)):
        process_videos(channel_ids[i], channel_name[i], 1)
