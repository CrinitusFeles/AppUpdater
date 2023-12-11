

from app_updater.check_for_update import check_for_updates, download_release


if __name__ == '__main__':
    release = check_for_updates("OAI-NSU", "KPA-GUI", 'MY_TOKEN')
    if release:
        download_release(release)