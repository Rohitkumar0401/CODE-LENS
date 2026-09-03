import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlparse

# backend directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Where cloned repositories will be stored
REPOSITORIES_DIR = BASE_DIR / "data" / "repositories"

# Create the directory if it does not exist
REPOSITORIES_DIR.mkdir(parents=True, exist_ok=True)


def validate_github_url(github_url: str):
    """
    Validate that the given URL belongs to GitHub
    and contains a repository path.
    """

    parsed_url = urlparse(github_url)

    # Check HTTPS
    if parsed_url.scheme != "https":
        raise ValueError("Only HTTPS GitHub URLs are allowed")

    # Check GitHub domain
    if parsed_url.netloc.lower() not in [
        "github.com",
        "www.github.com"
    ]:
        raise ValueError("Only GitHub repository URLs are allowed")

    # Check that URL contains username/repository
    parts = parsed_url.path.strip("/").split("/")

    if len(parts) < 2:
        raise ValueError("Invalid GitHub repository URL")

    return True


def clone_repository(github_url: str):
    """
    Clone a GitHub repository into the CodeLens storage directory.
    """

    # Validate URL before cloning
    validate_github_url(github_url)

    # Generate unique repository ID
    repository_id = str(uuid.uuid4())

    # Create local path
    repository_path = REPOSITORIES_DIR / repository_id

    try:

        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                github_url,
                str(repository_path)
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Git returned an error
        if result.returncode != 0:

            # Remove partially created folder if it exists
            if repository_path.exists():
                import shutil
                shutil.rmtree(repository_path)

            raise RuntimeError(
                "Failed to clone repository: "
                + result.stderr.strip()
            )

        return {
            "repository_id": repository_id,
            "github_url": github_url,
            "local_path": str(repository_path),
            "message": "Repository cloned successfully"
        }

    except subprocess.TimeoutExpired:

        if repository_path.exists():
            import shutil
            shutil.rmtree(repository_path)

        raise RuntimeError(
            "Repository cloning timed out"
        )

    except FileNotFoundError:

        raise RuntimeError(
            "Git is not installed or not available in PATH"
        )