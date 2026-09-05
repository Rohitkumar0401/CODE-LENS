import os
import stat
import shutil
from git import Repo

def _remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clone_repository(github_url: str) -> str:
    repo_name = github_url.rstrip("/").split("/")[-1]
    owner = github_url.rstrip("/").split("/")[-2]
    dest_path = os.path.join("data", "repos", f"{owner}__{repo_name}")

    if os.path.exists(dest_path):
        shutil.rmtree(dest_path, onerror=_remove_readonly)

    Repo.clone_from(github_url, dest_path)
    return dest_path