import os
import re
import pysrt
import requests
import json
from moviepy.editor import VideoFileClip, concatenate_videoclips
from itertools import starmap

srt_filename = "twinflames.srt"
video_file = "twinflames.mp4"

def get_ollama_summary(prompt):
    url = "http://omni.us-east-1.staging.shaadi.internal:11434/api/generate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "llama3.2:3b",
        "prompt": prompt
    }

    # Initialize an empty string to store the final response
    full_response = ""

    # Make a streaming request to Ollama
    response = requests.post(url, headers=headers, json=payload, stream=True)

    # Process each chunk as it arrives
    for chunk in response.iter_lines(decode_unicode=True):
        if chunk:
            # Parse each chunk as a JSON object
            data = json.loads(chunk)
            full_response += data.get("response", "")
            if data.get("done", False):
                break

    return full_response

def generate_summary_with_llm(srt_file, audience_demographic, n_sentences):
    """Generate a subtitle summary using Ollama LLM with target demographic in mind.

    Args:
        srt_file (str): The SRT file name.
        audience_demographic (str): Target audience demographic description.
        n_sentences (int): Approximate number of sentences in summary.

    Returns:
        list: Top sentences from the subtitles with index and timestamps.
    """
    text = srt_to_txt(srt_file)
    
    prompt = f"Summarize the following subtitles for a video, targeting {audience_demographic} audience. Provide a concise, {n_sentences}-sentence summary with timestamps:\n\n{text}"
    
    # Make a request to the Ollama API
    response = get_ollama_summary(prompt)
    print(response)
    
    if response:
        return extract_summary_with_timestamps(response, srt_file)
    else:
        raise Exception("Failed to get summary from Ollama.")

def srt_to_txt(srt_file):
    """Convert SRT file to plain text."""
    text = ''
    for index, item in enumerate(srt_file):
        if item.text.startswith("["):
            continue
        text += f"({index}) " + item.text.replace("\n", "").strip("...") + ". "
    return text

def extract_summary_with_timestamps(summary_text, srt_file):
    """Parse the LLM's summary with timestamps back to segments."""
    segment = []
    for line in summary_text.splitlines():
        match = re.search(r"\((\d+)\)", line)
        if match:
            index = int(match.group(1))
            item = srt_file[index]
            segment.append(srt_segment_to_range(item))
    return segment

def srt_segment_to_range(item):
    """Get timestamp range for each subtitle."""
    start = item.start.hours * 3600 + item.start.minutes * 60 + item.start.seconds + item.start.milliseconds / 1000
    end = item.end.hours * 3600 + item.end.minutes * 60 + item.end.seconds + item.end.milliseconds / 1000
    return start, end

def time_regions(regions):
    """Calculate total time duration for summary segments."""
    return sum(starmap(lambda start, end: end - start, regions))

def find_summary_regions(srt_filename, audience_demographic, duration=10):
    """Generate summary regions for video trimming."""
    srt_file = pysrt.open(srt_filename, encoding='utf-8')
    
    # Estimate sentence count based on desired duration
    subtitle_duration = time_regions(map(srt_segment_to_range, srt_file)) / len(srt_file)
    n_sentences = int(duration / subtitle_duration)
    print(subtitle_duration)
    print(n_sentences)

    summary = generate_summary_with_llm(srt_file, audience_demographic, n_sentences)
    total_time = time_regions(summary)
    
    # Adjust sentence count if duration doesn't match
    if total_time < duration:
        while total_time < duration:
            n_sentences += 1
            summary = generate_summary_with_llm(srt_file, audience_demographic, n_sentences)
            total_time = time_regions(summary)
    else:
        while total_time > duration:
            n_sentences -= 1
            summary = generate_summary_with_llm(srt_file, audience_demographic, n_sentences)
            total_time = time_regions(summary)
    
    return summary

def create_summary(filename, regions):
    """Create video summary by trimming and concatenating segments."""
    subclips = []
    input_video = VideoFileClip(filename)
    for (start, end) in regions:
        subclip = input_video.subclip(start, end)
        subclips.append(subclip)
    return concatenate_videoclips(subclips)

def get_summary(filename=video_file, subtitles=srt_filename, audience_demographic="general audience", duration=300):
    """Put everything together to generate video summary based on audience."""
    regions = find_summary_regions(subtitles, audience_demographic, duration)
    summary_video = create_summary(filename, regions)
    output = f"{os.path.splitext(filename)[0]}_summary.mp4"
    summary_video.to_videofile(output, codec="libx264", temp_audiofile="temp.m4a", remove_temp=True, audio_codec="aac")
    return output

# Usage
get_summary(audience_demographic="teen audience")
