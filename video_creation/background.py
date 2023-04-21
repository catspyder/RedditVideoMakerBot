import json
import random
import re
from pathlib import Path
from random import randrange
from typing import Any, Tuple,Dict

from moviepy.editor import VideoFileClip,AudioFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from pytube import YouTube
from pytube.cli import on_progress
from utils import settings
from utils.console import print_step, print_substep

def load_background_options():
    background_options = {}
    # Load background videos
    with open("./utils/background_videos.json") as json_file:
        background_options["video"] = json.load(json_file)

    # Load background audios
    with open("./utils/background_audios.json") as json_file:
        background_options["audio"] = json.load(json_file)
    
    # Remove "__comment" from backgrounds
    background_options["video"].pop("__comment", None)
    background_options["audio"].pop("__comment", None)
    
    # Add position lambda function
    # (https://zulko.github.io/moviepy/ref/VideoClip/VideoClip.html#moviepy.video.VideoClip.VideoClip.set_position)
    for name in list(background_options["video"].keys()):
        pos = background_options["video"][name][3]

        if pos != "center":
            background_options["video"][name][3] = lambda t: ("center", pos + t)

    return background_options



def get_start_and_end_times(video_length: int, length_of_clip: int) -> Tuple[int, int]:
    """Generates a random interval of time to be used as the background of the video.

    Args:
        video_length (int): Length of the video
        length_of_clip (int): Length of the video to be used as the background

    Returns:
        tuple[int,int]: Start and end time of the randomized interval
    """
    random_time = randrange(180, int(length_of_clip) - int(video_length))
    return random_time, random_time + video_length


def get_background_config(mode: str):
    """Fetch the background/s configuration"""
    try:
        choice = str(
            settings.config["settings"]["background"][f"background_{mode}"]
        ).casefold()
    except AttributeError:
        print_substep("No background selected. Picking random background'")
        choice = None

    # Handle default / not supported background using default option.
    # Default : pick random from supported background.
    if not choice or choice not in background_options[mode]:
        choice = random.choice(list(background_options[mode].keys()))

    return background_options[mode][choice]

def download_background_video(background_config: Tuple[str, str, str, Any]):
    """Downloads the background/s video from YouTube."""
    Path("./assets/backgrounds/video/").mkdir(parents=True, exist_ok=True)
    # note: make sure the file name doesn't include an - in it
    uri, filename, credit, _ = background_config
    if Path(f"assets/backgrounds/video/{credit}-{filename}").is_file():
        return
    print_step(
        "We need to download the backgrounds videos. they are fairly large but it's only done once. 😎"
    )
    print_substep("Downloading the backgrounds videos... please be patient 🙏 ")
    print_substep(f"Downloading {filename} from {uri}")
    YouTube(uri, on_progress_callback=on_progress).streams.filter(
        res="1080p"
    ).first().download("assets/backgrounds/video", filename=f"{credit}-{filename}")
    print_substep("Background video downloaded successfully! 🎉", style="bold green")

def download_background_audio(background_config: Tuple[str, str, str]):
    """Downloads the background/s audio from YouTube."""
    Path("./assets/backgrounds/audio/").mkdir(parents=True, exist_ok=True)
    # note: make sure the file name doesn't include an - in it
    uri, filename, credit = background_config
    if Path(f"assets/backgrounds/audio/{credit}-{filename}").is_file():
        return
    print_step(
        "We need to download the backgrounds audio. they are fairly large but it's only done once. 😎"
    )
    print_substep("Downloading the backgrounds audio... please be patient 🙏 ")
    print_substep(f"Downloading {filename} from {uri}")
    YouTube(uri, on_progress_callback=on_progress).streams.filter(only_audio=True).first().download("assets/backgrounds/audio", filename=f"{credit}-{filename}")
    print_substep("Background audio downloaded successfully! 🎉", style="bold green")

def chop_background(
    background_config: Dict[str,Tuple[str, str, str, Any]], video_length: int, reddit_object: dict
):
    """Generates the background footage to be used in the video and writes it to assets/temp/background.mp4

    Args:
        background_config (Tuple[str, str, str, Any]) : Current background configuration
        video_length (int): Length of the clip where the background footage is to be taken out of
    """

    print_step("Finding a spot in the backgrounds video to chop...✂️")
    video_choice = f"{background_config['video'][2]}-{background_config['video'][1]}"
    audio_choice = f"{background_config['audio'][2]}-{background_config['audio'][1]}"
    id = re.sub(r"[^\w\s-]", "", reddit_object["thread_id"])
    background_video = VideoFileClip(f"assets/backgrounds/video/{video_choice}")
    background_audio = AudioFileClip(f"assets/backgrounds/audio/{audio_choice}")
    start_time_video, end_time_video = get_start_and_end_times(video_length, background_video.duration)
    start_time_audio, end_time_audio = get_start_and_end_times(video_length, background_audio.duration)
    background_audio.subclip(start_time_audio,end_time_audio)
    background_video.set_audio(background_audio)

    try:
        ffmpeg_extract_subclip(
            f"assets/backgrounds/video/{video_choice}",
            start_time_video,
            end_time_video,
            targetname=f"assets/temp/{id}/background.mp4",
        )
    except (OSError, IOError):  # ffmpeg issue see #348
        print_substep("FFMPEG issue. Trying again...")
        with VideoFileClip(f"assets/backgrounds/video/{video_choice}") as video:
            new = video.subclip(start_time_video, end_time_video)
            new.write_videofile(f"assets/temp/{id}/background.mp4")
    print_substep("Background video chopped successfully!", style="bold green")
    return background_config[2]

# Create a tuple for downloads background (background_audio_options, background_video_options)
background_options = load_background_options()