from __future__ import unicode_literals
import os
import re
import requests
import pysrt
import chardet
from pydub import AudioSegment, silence
from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx, AudioFileClip, CompositeAudioClip
from moviepy.audio.fx.all import volumex

srt_filename = "./subtitles/plus-minus.srt"
video_file = "./videos/plus-minus.mp4"
background_music_file = "./music/cheerful.mp3"

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
            clip = clip.fx(vfx.fadein, duration=0.05).fx(vfx.fadeout, duration=0.05)
    
        subclips.append(clip)

    video_summary = concatenate_videoclips(subclips)

    # Load the background music
    background_music = AudioFileClip(background_music_file)

    # Adjust the background music to match the duration of the video summary
    if background_music.duration < video_summary.duration:
        background_music = background_music.loop(duration=video_summary.duration)
    else:
        background_music = background_music.subclip(0, video_summary.duration)
    
    # Extract the audio from the video summary for analysis
    video_audio = video_summary.audio
    video_audio_path = "temp_video_audio.wav"
    video_audio.write_audiofile(video_audio_path)

    # Analyze the audio to detect speech
    audio_segment = AudioSegment.from_file(video_audio_path)
    silence_threshold = -30  # in dB
    min_silence_len = 500    # in ms
    chunks = silence.detect_nonsilent(audio_segment, min_silence_len=min_silence_len, silence_thresh=silence_threshold)

    # Adjust the background music volume based on speech presence
    volume_adjusted_music = background_music.fx(volumex, 0.5)  # Lower volume when speech is present
    adjusted_clips = []
    for start, end in chunks:
        start /= 1000.0  # Convert ms to seconds
        end /= 1000.0
        adjusted_clips.append(background_music.subclip(start, end).fx(volumex, 0.3))
        adjusted_clips.append(background_music.subclip(end, end).fx(volumex, 1.0))
    
    background_music = concatenate_videoclips(adjusted_clips)
    
    final_audio = CompositeAudioClip([video_summary.audio, background_music])
    final_audio.fps = video_summary.audio.fps
    video_summary = video_summary.set_audio(final_audio)

    return video_summary

def generate_summary(filename=video_file, subtitles=srt_filename, duration=120, demographic_keywords=None, music_file=background_music_file):
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
    
    summary_clip = create_video_summary(filename, summary_segments, music_file)
    output_file = f"./summary/{os.path.splitext(filename)[0]}_summary.mp4"
    summary_clip.to_videofile(output_file, codec="libx264", temp_audiofile="temp.m4a", remove_temp=True, audio_codec="aac")
    return True

# Example usage with demographic keywords and background music
generate_summary(demographic_keywords=["cheeful", "youth"])
