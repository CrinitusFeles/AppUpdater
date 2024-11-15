import asyncio
import json
from distutils.version import StrictVersion
from typing import Any, AsyncGenerator
import httpx
from httpx import HTTPError, Response
from loguru import logger
from tqdm.asyncio import tqdm


class Release:
    tag_name: str
    token: str
    zipball_url: str
    tarball_url: str
    exe_url: str = ''
    exe_name: str = ''
    body: str = ''
    file_size: int = 0
    download_progress: int = 0
    def __init__(self, dictionary: dict) -> None:
        for k, v in dictionary.items():
            setattr(self, k, v)
        _buf_list: list = [asset for asset in dictionary.get('assets', {})
                           if 'exe' in asset.get('name', '')]
        if len(_buf_list) > 0:
            exe_asset = _buf_list[0]
            self.exe_url = exe_asset.get('url', '')
            self.exe_name = exe_asset.get('name', '')

    def __str__(self) -> str:
        return f'tag_name: {self.tag_name}\n'\
               f'zipball_url: {self.zipball_url}\n'\
               f'tarball_url: {self.tarball_url}\n'\
               f'exe_name: {self.exe_name}\n'\
               f'exe_url: {self.exe_url}\n'\
               f'description: {self.body}\n'


async def make_request(url: str = '', token: str = '') -> str:
    try:
        async with httpx.AsyncClient() as client:
            if token:
                header: dict[str, str] = {'Authorization': f'token {token}'}
            else:
                header = {}
            response: Response = await client.get(url, headers=header)
            response.raise_for_status()
    except HTTPError as err:
        logger.error(f'HTTP error occurred. Probably incorrect url.\n{err}')
    except ConnectionError as err:
        logger.error(f'Can\'t connect to server. '\
                     f'Probably no internet connection.\n{err}')
    else:
        return response.content.decode('utf-8')
    return ''


def compare_version(v1: str, v2: str) -> bool:
    if len(v1) > 0 and len(v2) > 0:
        try:
            _v1: str = v1.replace('v', '')
            _v2: str = v2.replace('v', '')
            return StrictVersion(_v1) > StrictVersion(_v2)
        except ValueError as ex:
            logger.error(ex)
            logger.error(v1, v2)
    return False


async def download_release(release: Release,
                           rename='') -> AsyncGenerator[int, Any]:
    try:
        # download the body of response by chunk, not immediately
        filename: str = rename or release.exe_name
        header: dict[str, str] = {'Authorization': f'token {release.token}',
                                  'Accept': 'application/octet-stream'}

        client = httpx.AsyncClient(follow_redirects=True)
        async with client.stream("GET", release.exe_url, headers=header) as r:
            total = int(r.headers["Content-Length"])
            release.file_size = total
            with open(filename, 'wb') as f:
                with tqdm(desc=f"Downloading {release.exe_name}",
                            total=total, unit_scale=True,
                            unit_divisor=1024, unit="B") as progress:
                    counter: int = r.num_bytes_downloaded
                    async for chunk in r.aiter_bytes(1024):
                        f.write(chunk)
                        progress.update(r.num_bytes_downloaded - counter)
                        counter = r.num_bytes_downloaded
                        yield int(counter / total * 100)

    except PermissionError as err:
        logger.error("Probably you try to rewrite .exe which already running")
        raise err


async def get_latest_release(url: str, token: str = '') -> Release | None:
    try:
        result: str = await make_request(f"{url}/latest", token)
        # https://docs.github.com/en/rest/releases/releases#get-the-latest-release
        if result != '':
            return Release(json.loads(result))
        return None
    except AttributeError as err:
        logger.error(err)
        return None


async def get_releases_list(url: str, token: str = '') -> list[Release] | None:
    try:
        result: str = await make_request(url, token)
        return [Release(release) for release in json.loads(result)]
    except AttributeError as err:
        logger.error(err)
        return None


async def check_for_updates(url: str, token: str = '',
                            current_version: str = '0.0.1') -> Release | None:
    latest_release: Release | None = await get_latest_release(url, token)
    if latest_release is not None:
        latest_release.token = token
        if compare_version(latest_release.tag_name, current_version):
            logger.info(f'There is new version:\n{latest_release}')
            return latest_release
        if compare_version(current_version, latest_release.tag_name):
            logger.warning(f'Warning! You did not update repository release! '\
                           f'Your current version {current_version} fresher' \
                           f'then latest repo {latest_release.tag_name}')
        else:
            logger.info('You use the latest version')
        return None
    logger.info('There are no new releases')
    return None


async def main():
    url = ''
    token = ''
    release: Release | None = await check_for_updates(url, token)
    if release:
        async for progress in download_release(release):
            ...

if __name__ == '__main__':
    asyncio.run(main())

    # releases_list = get_releases_list("OAI-NSU", "KPA-GUI")
    # if releases_list is not None:
    #     for release in releases_list:
    #         print(release)
