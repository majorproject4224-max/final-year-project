"""Download the unchanged, checksum-pinned official Stack Overflow 2024 release."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REVISION = "9dd5c163b7ec09ce5503f711c37a99dbd80ff3c7"
BASE = f"https://media.githubusercontent.com/media/StackExchange/Survey/{REVISION}/packages/archive/2024"
FILES = {
    "results.csv": "7f2c2dbf6989d00b80a7351de4bb3af4b52b21cc52d5c947891bbc4f4e5cbe49",
    "schema.csv": "d9c03fd43949dd9b0fea4847894c4011a6fe3c4390d5d8c48e078a8bfe623833",
}


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(destination=ROOT / "dataset" / "raw" / "stackoverflow2024"):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": "Stack Overflow Developer Survey 2024",
        "publisher": "Stack Exchange, Inc.",
        "source_revision": REVISION,
        "data_license": "ODbL-1.0",
        "contents_license": "DbCL-1.0",
        "attribution_url": "https://github.com/StackExchange/Survey#license-and-data-attribution",
        "methodology_url": "https://survey.stackoverflow.co/2024/methodology",
        "synthetic": False,
        "files": {},
    }
    for name, expected in FILES.items():
        path = destination / name
        url = f"{BASE}/{name}"
        if not path.exists() or checksum(path) != expected:
            temporary = path.with_suffix(".download")
            print(f"Downloading official {name} ...", flush=True)
            with urlopen(url, timeout=180) as response, temporary.open("wb") as output:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    output.write(chunk)
            if checksum(temporary) != expected:
                raise ValueError(f"Checksum mismatch for {name}; refusing changed/unverified data.")
            temporary.replace(path)
        manifest["files"][name] = {"url": url, "sha256": expected, "bytes": path.stat().st_size}
        print(f"Verified {name}: {expected}", flush=True)
    (destination / "source.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    download()
