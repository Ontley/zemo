import os
import pytube
from attrs import define
from googleapiclient.discovery import build
from dotenv import load_dotenv
load_dotenv()


YOUTUBE_TOKEN = os.environ.get('YOUTUBE_TOKEN')
if YOUTUBE_TOKEN is None:
    raise ValueError('No YOUTUBE_TOKEN found in environment')


__all__ = [
    'Song',
    'find_video'
]


@define(kw_only=True)
class Song:
    title: str
    channel_name: int
    thumbnail: str
    page_url: str
    url: str
    duration: int

    def __str__(self) -> str:
        return f'[{self.title}]({self.page_url})'

    def __repr__(self) -> str:
        return f'Song([{self.title}]({self.page_url}))'


# ytdl_opts = {
#     'format': 'bestaudio/best',
#     'postprocessors': [{
#         'key': 'FFmpegExtractAudio',
#         'preferredcodec': 'mp3',
#         'preferredquality': '192',
#     }],
#     'quiet': True,
#     'progress_hooks': []
# }


def find_video(arg: str) -> Song:
    '''Returns Song object with info extracted from first video found'''
    with build('youtube', 'v3', developerKey=YOUTUBE_TOKEN) as yt_service:
        request = yt_service.search().list(
            part='snippet',
            type='video',
            maxResults=1,
            q=arg
        )
        # wtf is the youtube api
        video_id = request.execute()['items'][0]['id']['videoId']
    video = pytube.YouTube(f'http://youtube.com/watch?v={video_id}')
    video.streams.get_audio_only().url

    # pprint(video, best_audio)
    return Song(
        title=video.title,
        channel_name=video.author,
        thumbnail=video.thumbnail_url,
        page_url=video.watch_url,
        url=video.streams.get_audio_only().url,
        duration=video.length
    )


if __name__ == '__main__':
    find_video('amogus')
