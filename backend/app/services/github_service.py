import shutil
import re
from pathlib import Path
from git import Repo, GitCommandError

# Base directory where all cloned repos will live
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "repos"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def extract_repo_name(github_url: str) -> str:
    """
    Extracts a clean repo name from a GitHub URL.
    e.g. https://github.com/user/repository.git -> user__repository
    """
    match = re.search(r"github\.com/([^/]+)/([^/]+?)(\.git)?/?$", github_url.strip())
    if not match:
        raise ValueError("Invalid GitHub URL")
    owner, repo = match.group(1), match.group(2)
    return f"{owner}__{repo}"


def clone_repository(github_url: str) -> dict:
    """
    Clones a GitHub repository into the local data/repos directory.
    Returns metadata about the cloned repo.
    """
    if not github_url or "github.com" not in github_url:
        raise ValueError("Please provide a valid GitHub URL")

    repo_name = extract_repo_name(github_url)
    local_path = DATA_DIR / repo_name

    if local_path.exists():
        shutil.rmtree(local_path)

    try:
        Repo.clone_from(github_url, local_path)
    except GitCommandError as e:
        raise RuntimeError(f"Failed to clone repository: {str(e)}")

    return {
        "repo_name": repo_name,
        "local_path": str(local_path),
        "status": "cloned"
    }