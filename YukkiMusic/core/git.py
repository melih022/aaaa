#
# Git auto-updater — disabled by default (set GIT_AUTO_UPDATE=true to enable).
# Auto-update from a remote upstream during cold start is dangerous in
# managed deployments and was the cause of long startup stalls.
#

import os

from ..logging import LOGGER


def git():
    if os.getenv("GIT_AUTO_UPDATE", "false").lower() not in ("1", "true", "yes"):
        LOGGER(__name__).info("Git auto-update disabled (set GIT_AUTO_UPDATE=true to enable).")
        return
    try:
        # Best-effort import & fetch only when explicitly enabled.
        from git import Repo
        from git.exc import InvalidGitRepositoryError

        import config

        try:
            repo = Repo()
            LOGGER(__name__).info("Git repo bulundu; fetch atlanıyor (manuel olarak çalıştırın).")
        except InvalidGitRepositoryError:
            LOGGER(__name__).info(
                f"Burası git repo değil; ister misiniz manuel olarak `git clone {config.UPSTREAM_REPO}` yapın."
            )
    except Exception as e:
        LOGGER(__name__).warning(f"Git updater skipped: {e}")
