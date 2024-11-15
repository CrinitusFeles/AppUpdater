import asyncio
from app_updater.check_for_update import check_for_updates, download_release


async def main():
    url: str = ''
    token: str = ''
    release = await check_for_updates(url, token)
    if release:
        async for progress in download_release(release):
            ...


if __name__ == '__main__':
    asyncio.run(main())