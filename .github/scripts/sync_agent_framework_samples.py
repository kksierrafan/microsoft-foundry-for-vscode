from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDER = "{{SafeProjectName}}"
UPSTREAM_REPO_API = "https://api.github.com/repos/microsoft/agent-framework/contents"
ALLOWED_SUFFIXES = {".cs", ".csproj"}


@dataclass(frozen=True)
class SampleConfig:
    upstream_name: str
    target_dir: Path

    @property
    def upstream_path(self) -> str:
        return f"dotnet/samples/05-end-to-end/HostedAgents/{self.upstream_name}"


SAMPLES = (
    SampleConfig(
        upstream_name="FoundrySingleAgent",
        target_dir=REPO_ROOT / "samples" / "hosted-agent" / "dotnet" / "agent",
    ),
    SampleConfig(
        upstream_name="FoundryMultiAgent",
        target_dir=REPO_ROOT / "samples" / "hosted-agent" / "dotnet" / "workflow",
    ),
)


def fetch_json(url: str) -> list[dict[str, object]]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "microsoft-foundry-for-vscode-sync",
        },
    )
    with urlopen(request) as response:
        return json.load(response)


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "microsoft-foundry-for-vscode-sync"})
    with urlopen(request) as response:
        return response.read().decode("utf-8")


def normalize_content(content: str, upstream_name: str) -> str:
    return content.replace(upstream_name, PLACEHOLDER)


def normalize_relative_path(relative_path: Path, upstream_name: str) -> Path:
    normalized_parts = [part.replace(upstream_name, PLACEHOLDER) for part in relative_path.parts]
    return Path(*normalized_parts)


def list_relevant_files(upstream_path: str) -> list[dict[str, object]]:
    items = fetch_json(f"{UPSTREAM_REPO_API}/{upstream_path}?ref=main")
    relevant_files: list[dict[str, object]] = []

    for item in items:
        item_type = item.get("type")
        item_path = str(item["path"])

        if item_type == "dir":
            relevant_files.extend(list_relevant_files(item_path))
            continue

        if item_type != "file":
            continue

        if Path(str(item["name"])).suffix not in ALLOWED_SUFFIXES:
            continue

        relevant_files.append(item)

    return relevant_files


def sync_sample(config: SampleConfig) -> list[Path]:
    items = list_relevant_files(config.upstream_path)
    expected_paths: list[Path] = []

    for item in items:
        download_url = str(item["download_url"])
        relative_upstream_path = Path(str(item["path"])).relative_to(config.upstream_path)
        target_relative_path = normalize_relative_path(relative_upstream_path, config.upstream_name)
        target_path = config.target_dir / target_relative_path
        normalized_content = normalize_content(fetch_text(download_url), config.upstream_name)

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(normalized_content, encoding="utf-8", newline="\n")
        expected_paths.append(target_path)

    expected_path_set = set(expected_paths)
    for existing_path in config.target_dir.rglob("*"):
        if existing_path.suffix not in ALLOWED_SUFFIXES:
            continue
        if existing_path not in expected_path_set:
            existing_path.unlink()

    for existing_dir in sorted((path for path in config.target_dir.rglob("*") if path.is_dir()), reverse=True):
        if not any(existing_dir.iterdir()):
            existing_dir.rmdir()

    return expected_paths


def main() -> None:
    synced_paths: list[Path] = []
    for sample in SAMPLES:
        synced_paths.extend(sync_sample(sample))

    for path in sorted(synced_paths):
        print(path.relative_to(REPO_ROOT).as_posix())


if __name__ == "__main__":
    main()
