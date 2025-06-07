#  YouTube Channel Video Summary to Email

This repository provides a Python script to fetch the latest videos from specified YouTube channels, extract their transcripts, summarize the content using OpenAI's GPT models, and send those summaries via email using the Brevo API. The script is designed for automation and can be scheduled to run periodically.

## Features

- Fetches recent videos from multiple YouTube channels.
- Extracts transcripts from videos (if available).
- Summarizes video content using OpenAI's GPT models (configurable).
- Sends summarized content via email (Brevo).
- Logging for monitoring and debugging.
- Modular design for easy extension.

## Requirements

- Python 3.7+
- Google API Key (for YouTube Data API)
- OpenAI API Key
- Brevo API Key (for sending emails)
- (Optional) Twilio credentials if SMS integration is needed

## Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/vinayOcta32724/youtubesummaryrepo.git
   cd youtubesummaryrepo
   ```

2. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

3. Fill in your API keys in `youtube_channel_video_summary_to_email.py` or use environment variables.

## Usage

Run the script with:

```sh
python youtube_channel_video_summary_to_email.py
```

The script will:
- Fetch videos from the list of channel IDs specified in the script.
- Summarize each video published within the last day (can be configured).
- Email the summary to the configured recipient.

## Configuration

- Edit the following variables in `youtube_channel_video_summary_to_email.py`:
    - `openai_api_key`
    - `YOUTUBE_API_KEY`
    - `brevo_api_key`
    - `receipient_email`
    - `channel_ids` and `channel_name` arrays

## Logging

- Logs are saved in `youtube_summary.log` in the script directory, with daily rotation and 30-day retention.

## Extending

- To change the summary model, edit the `openai_model` variable.
- To change the email provider, update the `send_email_via_brevo` function.
- For different scheduling, use a task scheduler like cron.

## License

This project is licensed under the MIT License.

## Disclaimer

- The script may not work for videos without transcripts or if APIs return errors.
- Use appropriate API rate limits to avoid blocks.

## Author

Created by [vinayOcta32724](https://github.com/vinayOcta32724)
