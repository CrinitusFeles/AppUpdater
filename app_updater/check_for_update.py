import json
from distutils.version import StrictVersion
import os
from typing import Optional
from requests import HTTPError, ConnectionError
import requests
from tqdm import tqdm


gh_token = os.environ.get('GH_TOKEN', '')

__version__ = '0.0.1'

class Release:
    name: str
    token: str
    zipball_url: str
    tarball_url: str
    exe_url: str = ''
    exe_name: str = ''
    body: str = ''
    file_size: int = 0
    download_progress: int = 0
    __byte_counter: int = 0
    def __init__(self, dictionary: dict) -> None:
        for k, v in dictionary.items():
            setattr(self, k, v)
        __buf_list = [asset for asset in dictionary.get('assets', {}) if 'exe' in asset.get('name', '')]
        if len(__buf_list) > 0:
            exe_asset = __buf_list[0]
            self.exe_url = exe_asset.get('url', '')
            self.exe_name = exe_asset.get('name', '')

    def progress_update(self, size: int) -> int:
        self.__byte_counter += size
        self.download_progress = round((self.__byte_counter / self.file_size) * 100)
        return self.download_progress

    def __str__(self) -> str:
        return f'name: {self.name}\nzipball_url: {self.zipball_url}\ntarball_url: {self.tarball_url}\n'\
               f'exe_name: {self.exe_name}\nexe_url: {self.exe_url}\ndescription: {self.body}\n'


def make_request(url: str = '', token: str = '') -> str:
    if url != '':
        try:
            if token != '':
                response = requests.get(url, headers={'Authorization': f'token {token}'})
            else:
                response = requests.get(url)
            response.raise_for_status()
        except HTTPError as http_err:
            print(f'HTTP error occurred. Probably incorrect url.\n{http_err}')
        except ConnectionError as err:
            print(f'Can\'t connect to server. Probably no internet connection.\n{err}')
        else:
            return response.content.decode('utf-8')
    else:
        raise Exception('make_request got empty url')
    return ''


def compare_version(v1: str, v2: str) -> bool:
    if len(v1) > 0 and len(v2) > 0:
        try:
            return StrictVersion(v1.replace('v', '')) > StrictVersion(v2.replace('v', ''))
        except ValueError as ex:
            print(ex)
            print(v1, v2)
    return False

def download_release(latest_release: Release, rename=''):
    try:
        # download the body of response by chunk, not immediately
        if latest_release.token != '':
            response = requests.get(latest_release.exe_url, stream=True,
                                    headers={'Authorization': f'token {latest_release.token}',
                                             'Accept': 'application/octet-stream'})
        else:
            response = requests.get(latest_release.exe_url, stream=True,
                        headers={'Accept': 'application/octet-stream'})
        file_size: int = int(response.headers.get("Content-Length", 0))  # get the total file size
        latest_release.file_size = file_size
        print(f'{file_size=}')
        progress = tqdm(response.iter_content(1024), f"Downloading {latest_release.exe_name}", total=file_size,
                        unit="B", unit_scale=True, unit_divisor=1024)
        filename: str = latest_release.exe_name if rename == '' else rename
        if not filename.lower().endswith('.exe'):
            filename += '.exe'
        with open(filename, "wb") as f:
            for data in progress.iterable:
                f.write(data)  # write data read to the file
                progress.update(len(data))  # update the progress bar manually
                latest_release.progress_update(len(data))
        return 0
    except PermissionError as err:
        print(err)
        print("Probably you try to rewrite .exe which already running")
        return 1


def get_latest_release(repo: str, owner: str, token: str = '') -> Optional[Release]:
    try:
        result: str = make_request(f"https://api.github.com/repos/{repo}/{owner}/releases/latest", token)
        # https://docs.github.com/en/rest/releases/releases#get-the-latest-release
        if result != '':
            return Release(json.loads(result))
        return None
    except AttributeError as err:
        print(err)
        return None

def get_releases_list(repo: str, owner: str, token: str = '') -> Optional[list[Release]]:
    try:
        result: str = make_request(f"https://api.github.com/repos/{repo}/{owner}/releases", token)
        return [Release(release) for release in json.loads(result)]
    except AttributeError as err:
        print(err)
        return None

def check_for_updates(repo: str, owner: str, token: str = '') -> Optional[Release]:
    latest_release: Optional[Release] = get_latest_release(repo, owner, token)
    if latest_release is not None:
        latest_release.token = token
        if compare_version(latest_release.name, __version__):
            print(f'There is new version:\n{latest_release}')
            return latest_release
        if compare_version(__version__, latest_release.name):
            print(f'Warning! You did not update repository release! Your current version {__version__} fresher' \
                  f'then latest repo {latest_release.name}')
        else:
            print('You use the latest version')
        return None
    print('There are no new releases')
    return None

if __name__ == '__main__':
    release = check_for_updates("OAI-NSU", "KPA-GUI", gh_token)
    if release:
        download_release(release)

    # releases_list = get_releases_list("OAI-NSU", "KPA-GUI")
    # if releases_list is not None:
    #     for release in releases_list:
    #         print(release)
