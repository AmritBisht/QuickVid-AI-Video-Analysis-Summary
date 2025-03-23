from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.generativeai import GenerativeModel  # Import Gemini API
from youtube_transcript_api import YouTubeTranscriptApi
import os
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip
import speech_recognition as sr
import re
import requests
import json
from typing import Optional, List
import uuid
from datetime import datetime
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from pytube import YouTube
from fastapi.responses import StreamingResponse
import io
import tempfile
import shutil
import google.generativeai as genai
from pydub import AudioSegment
import speech_recognition as sr
from fastapi import HTTPException


# Download NLTK resources
try:
    nltk.download('vader_lexicon', quiet=True)
except:
    pass

# Load environment variables
load_dotenv()

# Configure Gemini API key
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Gemini model
gemini_model = genai.GenerativeModel("gemini-2.0-flash-001")

app = FastAPI(title="Video Summary API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUMMARIES_DB = []

class VideoURL(BaseModel):
    url: str

class SummaryOptions(BaseModel):
    format: Optional[str] = "markdown"  # markdown, bullet, narrative
    length: Optional[str] = "medium"    # short, medium, long
    language: Optional[str] = "english" # target language for translation
    include_sentiment: Optional[bool] = False
    include_keywords: Optional[bool] = False

class SummaryRequest(BaseModel):
    url: str
    options: Optional[SummaryOptions] = SummaryOptions()

class SummaryResponse(BaseModel):
    id: str
    summary: str
    transcript: str
    metadata: dict

def extract_video_id(url):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return None

def get_video_metadata(video_id):
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        return {
            "title": yt.title,
            "author": yt.author,
            "length_seconds": yt.length,
            "views": yt.views,
            "publish_date": str(yt.publish_date) if yt.publish_date else None,
            "thumbnail_url": yt.thumbnail_url,
        }
    except Exception as e:
        print(f"Error getting metadata: {str(e)}")
        return {}

def get_video_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([item['text'] for item in transcript])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting transcript: {str(e)}")

def analyze_sentiment(text):
    try:
        sid = SentimentIntensityAnalyzer()
        sentiment = sid.polarity_scores(text)
        # Determine overall sentiment
        if sentiment['compound'] >= 0.05:
            overall = "positive"
        elif sentiment['compound'] <= -0.05:
            overall = "negative"
        else:
            overall = "neutral"
        return {
            "overall": overall,
            "scores": sentiment
        }
    except Exception as e:
        print(f"Error in sentiment analysis: {str(e)}")
        return {"overall": "unknown", "scores": {}}

def extract_keywords(text, num_keywords=10):
    try:
        # Simple frequency-based keyword extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_freq = {}
        # Common stopwords to exclude
        stopwords = ["the", "and", "this", "that", "for", "you", "with", "have", 
                    "from", "are", "they", "your", "what", "their", "can"]
        for word in words:
            if word not in stopwords:
                if word in word_freq:
                    word_freq[word] += 1
                else:
                    word_freq[word] = 1
        # Sort by frequency
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:num_keywords]]
    except Exception as e:
        print(f"Error extracting keywords: {str(e)}")
        return []


def split_and_transcribe(audio_path, language="en-US", chunk_length_ms=60000):
    try:
        audio = AudioSegment.from_wav(audio_path)
        recognizer = sr.Recognizer()

        # Split the audio into chunks of 60 seconds
        chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
        transcript = []

        for i, chunk in enumerate(chunks):
            chunk_path = f"{audio_path}_chunk_{i}.wav"
            chunk.export(chunk_path, format="wav")

            with sr.AudioFile(chunk_path) as source:
                audio_data = recognizer.record(source)

                try:
                    # Perform speech recognition on each chunk
                    text = recognizer.recognize_google(audio_data, language=language)
                    transcript.append(text)
                except sr.UnknownValueError:
                    transcript.append(f"[Chunk {i}: Speech not recognized]")
                except sr.RequestError as e:
                    raise HTTPException(status_code=500, detail=f"API Error: {e}")

        return " ".join(transcript)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {e}")



def get_summary_prompt(text, options):
    format_instruction = ""
    length_instruction = ""
    # Format instructions
    if options.format == "bullet":
        format_instruction = "Format the summary as bullet points."
    elif options.format == "narrative":
        format_instruction = "Format the summary as a narrative paragraph."
    else:  # markdown default
        format_instruction = "Format the summary using markdown with headings, bullet points, and emphasis where appropriate."
    # Length instructions
    if options.length == "short":
        length_instruction = "Keep the summary very concise (about 100-150 words)."
    elif options.length == "long":
        length_instruction = "Provide a comprehensive summary covering all major points (about 400-500 words)."
    else:  # medium default
        length_instruction = "Provide a balanced summary (about 250-300 words)."
    prompt = f"""Please summarize the following content:
{text}
{format_instruction} {length_instruction} Focus on the main ideas, key points, and conclusions.
Include the most important details while removing redundancy."""
    return prompt

def summarize_text(text, options=SummaryOptions()):
    try:
        # Generate summary using Gemini API
        prompt = get_summary_prompt(text, options)
        response = gemini_model.generate_content(prompt)
        summary = response.text
        
        # Translate if needed
        if options.language and options.language.lower() != "english":
            translation_prompt = f"Translate the following text to {options.language}: {summary}"
            translated_response = gemini_model.generate_content(translation_prompt)
            summary = translated_response.text
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@app.post("/summarize/youtube", response_model=SummaryResponse)
async def summarize_youtube(request: SummaryRequest):
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    # Get video metadata
    metadata = get_video_metadata(video_id)
    # Get transcript
    transcript = get_video_transcript(video_id)
    # Generate summary
    summary = summarize_text(transcript, request.options)
    # Additional analyses if requested
    if request.options.include_sentiment:
        metadata["sentiment"] = analyze_sentiment(transcript)
    if request.options.include_keywords:
        metadata["keywords"] = extract_keywords(transcript)
    # Create response
    summary_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    response = {
        "id": summary_id,
        "summary": summary,
        "transcript": transcript,
        "metadata": {
            **metadata,
            "timestamp": timestamp,
            "video_id": video_id,
            "options": request.options.dict() if request.options else {},
        }
    }
    # Store in database
    SUMMARIES_DB.append(response)
    return response

@app.post("/summarize/upload", response_model=SummaryResponse)
async def summarize_upload(
    file: UploadFile = File(...),
    format: str = Query("markdown"),
    length: str = Query("medium"),
    language: str = Query("english"),
    include_sentiment: bool = Query(False),
    include_keywords: bool = Query(False)
):
    try:
        options = SummaryOptions(
            format=format,
            length=length,
            language=language,
            include_sentiment=include_sentiment,
            include_keywords=include_keywords
        )

        temp_dir = tempfile.mkdtemp()
        try:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            video = VideoFileClip(file_path)
            audio_path = os.path.join(temp_dir, "temp_audio.wav")
            video.audio.write_audiofile(audio_path, codec='pcm_s16le', fps=16000, verbose=False, logger=None)

            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                raise HTTPException(status_code=500, detail="Audio extraction failed or resulted in an empty file")

            # Transcribe using the split and transcribe function
            transcript = split_and_transcribe(audio_path, language=language)

            summary = summarize_text(transcript, options)
            metadata = {
                "filename": file.filename,
                "duration_seconds": video.duration,
                "timestamp": datetime.now().isoformat()
            }

            if include_sentiment:
                metadata["sentiment"] = analyze_sentiment(transcript)
            if include_keywords:
                metadata["keywords"] = extract_keywords(transcript)

            summary_id = str(uuid.uuid4())
            response = {
                "id": summary_id,
                "summary": summary,
                "transcript": transcript,
                "metadata": metadata
            }
            SUMMARIES_DB.append(response)
            return response
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summaries")
async def get_summaries():
    """Return all summaries in the database"""
    return SUMMARIES_DB

@app.get("/summaries/{summary_id}")
async def get_summary(summary_id: str):
    """Return a specific summary by ID"""
    for summary in SUMMARIES_DB:
        if summary["id"] == summary_id:
            return summary
    raise HTTPException(status_code=404, detail="Summary not found")

@app.delete("/summaries/{summary_id}")
async def delete_summary(summary_id: str):
    """Delete a specific summary by ID"""
    global SUMMARIES_DB
    original_length = len(SUMMARIES_DB)
    SUMMARIES_DB = [s for s in SUMMARIES_DB if s["id"] != summary_id]
    if len(SUMMARIES_DB) == original_length:
        raise HTTPException(status_code=404, detail="Summary not found")
    return {"status": "success", "message": "Summary deleted"}

@app.get("/download/{summary_id}")
async def download_summary(summary_id: str, format: str = "txt"):
    """Download a summary in different formats"""
    # Find the summary
    summary_data = None
    for summary in SUMMARIES_DB:
        if summary["id"] == summary_id:
            summary_data = summary
            break
    if not summary_data:
        raise HTTPException(status_code=404, detail="Summary not found")
    content = ""
    media_type = "text/plain"
    filename = f"summary_{summary_id}"
    if format == "txt":
        content = f"Summary:\n{summary_data['summary']}\nTranscript:\n{summary_data['transcript']}"
        filename += ".txt"
    elif format == "json":
        content = json.dumps(summary_data, indent=2)
        media_type = "application/json"
        filename += ".json"
    elif format == "md":
        content = f"# Video Summary\n## Summary\n{summary_data['summary']}\n## Transcript\n{summary_data['transcript']}"
        media_type = "text/markdown"
        filename += ".md"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    return StreamingResponse(
        io.StringIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "api_version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)