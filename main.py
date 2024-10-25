from __future__ import unicode_literals
import os
import re
import pysrt
import chardet
from moviepy.editor import VideoFileClip, concatenate_videoclips
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
from sumy.summarizers.kl import KLSummarizer

import nltk
nltk.download('punkt_tab')

srt_filename = "video.srt"
video_file = "video.mp4"

def srt_to_text(srt_file):
    """Convert SRT file content to plain text."""
    text = ''
    for index, item in enumerate(srt_file):
        if not item.text.startswith("["):
            text += "(%d) " % index
            text += item.text.replace("\n", "").strip("...").replace(
                                     ".", "").replace("?", "").replace("!", "")
            text += ". "
    return text

def srt_segment_to_range(item):
    """Extract start and end timestamps from an SRT item."""
    start = item.start.hours * 3600 + item.start.minutes * 60 + item.start.seconds + item.start.milliseconds / 1000
    end = item.end.hours * 3600 + item.end.minutes * 60 + item.end.seconds + item.end.milliseconds / 1000
    return start, end

def summarize_srt(srt_file, n_sentences, language="english"):
    """Summarize SRT file content into n sentences."""
    parser = PlaintextParser.from_string(srt_to_text(srt_file), Tokenizer(language))
    summarizer = KLSummarizer(Stemmer(language))
    summarizer.stop_words = get_stop_words(language)
    
    summary = []
    for sentence in summarizer(parser.document, n_sentences):
        index = int(re.search(r"\((\d+)\)", str(sentence)).group(1))
        summary.append(srt_segment_to_range(srt_file[index]))
    return summary

def calculate_duration(segments):
    """Calculate total duration for given segments."""
    return sum(end - start for start, end in segments)

def find_summary_regions(srt_filename, duration=30, language="english"):
    """Identify summary regions within SRT file to match desired duration."""
    enc = chardet.detect(open(srt_filename, "rb").read())['encoding']
    srt_file = pysrt.open(srt_filename, encoding=enc)
    
    avg_duration = calculate_duration(map(srt_segment_to_range, srt_file)) / len(srt_file)
    n_sentences = int(duration / avg_duration)
    
    summary = summarize_srt(srt_file, n_sentences, language)
    while (total_duration := calculate_duration(summary)) < duration:
        n_sentences += 1
        summary = summarize_srt(srt_file, n_sentences, language)
    
    return summary

def create_video_summary(filename, regions):
    """Create a summarized video by concatenating specified segments."""
    input_video = VideoFileClip(filename)
    subclips = [input_video.subclip(start, end) for start, end in regions]
    return concatenate_videoclips(subclips)

def generate_summary(filename=video_file, subtitles=srt_filename, duration=120):
    """Generate the video summary."""
    regions = find_summary_regions(subtitles, duration)
    summary_clip = create_video_summary(filename, regions)
    output_file = f"{os.path.splitext(filename)[0]}_summary.mp4"
    summary_clip.to_videofile(output_file, codec="libx264", temp_audiofile="temp.m4a", remove_temp=True, audio_codec="aac")
    return True

generate_summary()
