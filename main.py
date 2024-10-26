from __future__ import unicode_literals
import os
import re
import requests
import pysrt
import chardet
from moviepy.editor import VideoFileClip, concatenate_videoclips

srt_filename = "./subtitles/plus-minus.srt"
video_file = "./videos/plus-minus.mp4"

OLLAMA_SERVER_URL = "http://omni.us-east-1.staging.shaadi.internal:11434/api/generate"

def call_ollama_server(prompt, model="llama3.2:3b"):
    """Send a prompt to the Ollama server and return the response."""
    response = requests.post(OLLAMA_SERVER_URL, json={"model": model, "prompt": prompt, "stream": False})
    print(response)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json().get("response", "").strip()

def srt_to_text(srt_file):
    """Convert SRT file content to plain text."""
    text = ''
    for index, item in enumerate(srt_file):
        if not item.text.startswith("["):
            text += f"({index}) " + item.text.replace("\n", " ").strip("...") + ". "
    return text

def srt_segment_to_range(item):
    """Extract start and end timestamps from an SRT item."""
    start = item.start.hours * 3600 + item.start.minutes * 60 + item.start.seconds + item.start.milliseconds / 1000
    end = item.end.hours * 3600 + item.end.minutes * 60 + item.end.seconds + item.end.milliseconds / 1000
    return start, end

def filter_srt_for_demographic_llm(srt_file, demographic_keywords):
    """Use LLM to filter SRT file content for relevance to the demographic."""
    filtered_segments = []
    for item in srt_file:
        prompt = (
            f"Given the following demographic keywords: {', '.join(demographic_keywords)}, identify if the "
            f"following text is relevant to the demographic. Respond with 'yes' or 'no'.\n\n"
            f"Text: {item.text}\n\n"
            "Response: <yes/no>"
        )
        response_text = call_ollama_server(prompt)
        if response_text.lower() == "yes":
            filtered_segments.append(item)
    return filtered_segments

def summarize_srt_llm(filtered_text, duration):
    """Use LLM to summarize filtered SRT text into a concise format."""
    prompt = (
        f"Summarize the following text to create a video summary that will fit into {duration} seconds. "
        "Provide the response in the format of indexed sentences for easy reference. "
        "Each sentence should be in the format (index) text. Only include the text for the summary.\n\n"
        f"Text: {filtered_text}\n\n"
        "Response: <summary>"
    )
    return call_ollama_server(prompt)

def calculate_duration(segments):
    """Calculate total duration for given segments."""
    return sum(end - start for start, end in segments)

def create_video_summary(filename, segments):
    """Create a summarized video by concatenating specified segments."""
    input_video = VideoFileClip(filename)
    subclips = [input_video.subclip(start, end) for start, end in segments]
    return concatenate_videoclips(subclips)

def generate_summary(filename=video_file, subtitles=srt_filename, duration=120, demographic_keywords=None):
    """Generate the video summary specific to a demographic using LLM for filtering and summarization."""
    enc = chardet.detect(open(subtitles, "rb").read())['encoding']
    srt_file = pysrt.open(subtitles, encoding=enc)
    
    if demographic_keywords:
        srt_file = filter_srt_for_demographic_llm(srt_file, demographic_keywords)
    
    if not srt_file:
        raise ValueError("No relevant segments found for the specified demographic keywords.")
    
    # Prepare text for summarization with LLM
    filtered_text = srt_to_text(srt_file)
    summary_text = summarize_srt_llm(filtered_text, duration)
    
    # Convert summary text to timestamp segments
    summary_segments = [
        srt_segment_to_range(srt_file[int(match.group(1))])
        for match in re.finditer(r"\((\d+)\)", summary_text)
    ]
    
    summary_clip = create_video_summary(filename, summary_segments)
    output_file = f"./summary/{os.path.splitext(filename)[0]}_summary.mp4"
    summary_clip.to_videofile(output_file, codec="libx264", temp_audiofile="temp.m4a", remove_temp=True, audio_codec="aac")
    return True

# Example usage with demographic keywords
generate_summary(demographic_keywords=["cheerful", "youth"])
