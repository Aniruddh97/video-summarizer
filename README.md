# Video Summarizer

This Python project uses Large Language Models (LLMs) to generate concise and engaging video summaries tailored to specific demographics. 

## Features

* **Demographic-Specific Summarization:**  Leverages the power of LLMs to analyze subtitles and identify segments most relevant to a target audience defined by keywords (e.g., "youth," "tech-savvy," "parents").
* **Concise Summaries:**  Generates summaries that fit within a specified duration, ensuring viewers get the most important information quickly.
* **Enhanced Viewing Experience:**  Adds background music to the summarized videos, dynamically adjusting volume during speech segments for optimal audio clarity.

## How it Works

1. **Subtitle Analysis:** The script reads subtitle files (SRT format) and extracts the text content.
2. **Demographic Filtering (Optional):** If demographic keywords are provided, an LLM is used to filter the subtitles, keeping only the segments relevant to the target audience.
3. **LLM-Powered Summarization:** The filtered subtitle text is sent to an LLM with a prompt to generate a concise summary that fits within the desired duration. The summary is structured with indexed sentences for easy reference.
4. **Video Editing:** The script uses the timestamps from the summarized sentences to extract corresponding video segments and concatenate them.
5. **Background Music Integration:** Background music is added to the summarized video, with volume automatically adjusted to ensure clarity during speech segments.
6. **Output:** The final summarized video is saved as an MP4 file.

## Requirements

* Python 3.6+
* Libraries: `pysrt`, `chardet`, `moviepy`, `sumy`, `nltk`, `pydub` (install using `pip install -r requirements.txt`)

## Usage

1. **Setup:**
   - Place your video file (e.g., `video.mp4`) in the `videos` directory.
   - Place the corresponding subtitle file (e.g., `video.srt`) in the `subtitles` directory.
   - (Optional) Place your desired background music file (e.g., `music.mp3`) in the `music` directory.
2. **Configuration:**
   - Update the `srt_filename`, `video_file`, and `background_music_file` variables in `main.py` to match your file names.
   - Set the desired summary duration in seconds by modifying the `duration` parameter in the `generate_summary` function call.
   - (Optional) Specify demographic keywords as a list in the `demographic_keywords` parameter of the `generate_summary` function.
3. **Run:**
   - Execute the script: `python main.py`

## Example

```python
generate_summary(demographic_keywords=["cheeful", "youth"])
