from __future__ import unicode_literals
import os
import re
import requests
import pysrt
import chardet
import concurrent.futures
from pydub import AudioSegment, silence
from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx, AudioFileClip, CompositeAudioClip
from moviepy.audio.fx.all import volumex

keywords = ["morbid", "death", "boring", "serious", "ignorant"]
srt_filename = "./subtitles/one-minute.srt"
video_file = "./videos/one-minute.mp4"
background_music_file = "./music/suspense.mp3"

OLLAMA_SERVER_URL = "http://172.32.27.52:11434/api/generate"

def call_ollama_server(prompt, model="llama3.2:3b"):
    """Send a prompt to the Ollama server and return the response."""
    response = requests.post(OLLAMA_SERVER_URL, json={"model": model, "prompt": prompt, "stream": False})
    response.raise_for_status()  # Raise an error for bad status codes
    reply = response.json().get("response", "").strip()
    # print({prompt: prompt, response: reply})
    return reply

def srt_to_text(srt_file):
    """Convert SRT file content to plain text."""
    text = []
    for index, item in enumerate(srt_file):
        if not item.text.startswith("["):
            text.append(f"({index}) " + item.text.replace("\n", " ").strip("..."))
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
            f"following text is relevant to the demographic. Respond only with either 'yes' or 'no'.\n\n"
            f"Text: {item.text}\n\n"
            "Response: "
        )
        response_text = call_ollama_server(prompt)
        if "yes" in response_text.lower():
            filtered_segments.append(item)
            
        print({"subtitle": item.text, "reply": response_text})

    return filtered_segments

import concurrent.futures

def filter_srt_for_demographic_llm_parallel(srt_file, demographic_keywords):
    """Use LLM to filter SRT file content for relevance to the demographic in parallel."""
    filtered_segments = []

    # Define the function to process each item in parallel
    def process_item(item):
        prompt = (
            f"Is the text related to the below labels in any way?\n"
            "Respond with only 'Yes' or 'No'\n\n"
            f"Text: {item.text}\n"
            f"Labels: {' '.join(demographic_keywords)}"
        )
        response_text = call_ollama_server(prompt)
        print({"subtitle": item.text, "reply": response_text})
        return item if "yes" in response_text.lower() else None

    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Map the function to each item in the srt_file list
        results = list(executor.map(process_item, srt_file))

    # Filter out None values from the results
    filtered_segments = [item for item in results if item is not None]

    return filtered_segments


def summarize_srt_llm(filtered_text_array, duration):
    """Use LLM to summarize filtered SRT text into a concise format."""
    prompt = (
        f"Re arrange the following array of (indexed) strings such that they become meaningful\n"
        f"Do not alter the array content, keep the indexes, just reorder them so that they make sense\n"
        f"However, you can remove an element if it doesn't fit or make sense\n"
        f"The output array should not exceed {duration/1.5} words\n"
        f"Reply only with the re arranged array and nothing else\n\n"
        f"Array: \n\n{filtered_text_array}\n\n"
    )
    response = call_ollama_server(prompt)
    
    print({"prompt": prompt, "response": response})

    return response

def calculate_duration(segments):
    """Calculate total duration for given segments."""
    return sum(end - start for start, end in segments)

def create_video_summary(filename, segments, background_music_file):
    """Create a summarized video by concatenating specified segments and adding background music."""
    input_video = VideoFileClip(filename)
    subclips = []
    
    for i, (start, end) in enumerate(segments):
        clip = input_video.subclip(start, end)
    
        # Add fade in for the first clip
        if i == 0:
            clip = clip.fx(vfx.fadeout, duration=0.5)
        # Add fade out for the last clip
        elif i == len(segments) - 1:
            clip = clip.fx(vfx.fadein, duration=0.5)
        # Add both fade in and fade out for middle clips
        else:
            clip = clip.fx(vfx.fadein, duration=0.1).fx(vfx.fadeout, duration=0.1)
    
        subclips.append(clip)

    video_summary = concatenate_videoclips(subclips)

    # Load the background music
    background_music = AudioFileClip(background_music_file)

    # Adjust the background music to match the duration of the video summary
    if background_music.duration < video_summary.duration:
        background_music = background_music.loop(duration=video_summary.duration)
    else:
        background_music = background_music.subclip(0, video_summary.duration)
    
    # Increase the main video audio volume
    video_audio = video_summary.audio.volumex(1.5)

    # Adjust the background music volume (lower it so it doesn't overpower the video audio)
    background_music = background_music.volumex(0.3)

    # Combine the video audio and background music
    final_audio = CompositeAudioClip([video_audio, background_music])
    video_summary = video_summary.set_audio(final_audio)

    return video_summary

def generate_summary(filename=video_file, subtitles=srt_filename, duration=120, demographic_keywords=None, music_file=background_music_file):
    """Generate the video summary specific to a demographic using LLM for filtering and summarization."""
    enc = chardet.detect(open(subtitles, "rb").read())['encoding']
    srt_file = pysrt.open(subtitles, encoding=enc)
    
    if demographic_keywords:
        srt_file = filter_srt_for_demographic_llm_parallel(srt_file, demographic_keywords)
    
    if not srt_file:
        print("No dialogues shortlisted!")
        return
    
    # Prepare text for summarization with LLM
    filtered_text_array = srt_to_text(srt_file)
    summary_text = summarize_srt_llm(filtered_text_array, duration)
    
    # Convert summary text to timestamp segments
    summary_segments = [
        srt_segment_to_range(srt_file[int(match.group(1))])
        for match in re.finditer(r"\((\d+)\)", summary_text)
    ]
    
    summary_clip = create_video_summary(filename, summary_segments, music_file)
    output_file = f"./summary/{os.path.splitext(os.path.basename(filename))[0]}_{keywords[0]}_summary.mp4"
    summary_clip.to_videofile(output_file, codec="libx264", temp_audiofile="temp.m4a", remove_temp=True, audio_codec="aac")
    return True

# Example usage with demographic keywords and background music
generate_summary(demographic_keywords=keywords)
