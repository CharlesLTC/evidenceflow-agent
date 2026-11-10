"""Install a verified portable GitHub CLI into ignored project .tools, without system changes."""

import hashlib
import io
import zipfile

import httpx

from evidenceflow.config import ROOT
from evidenceflow.trace_writer import write_json


def main():
    with httpx.Client(follow_redirects=True, timeout=90) as client:
        response = client.get("https://api.github.com/repos/cli/cli/releases/latest")
        response.raise_for_status()
        release = response.json()
        asset = next(a for a in release["assets"] if a["name"].endswith("windows_amd64.zip"))
        sums = next(a for a in release["assets"] if a["name"].endswith("checksums.txt"))
        checksum_response = client.get(sums["browser_download_url"])
        checksum_response.raise_for_status()
        expected = next(
            line.split()[0]
            for line in checksum_response.text.splitlines()
            if line.split()[-1] == asset["name"]
        )
        download = client.get(asset["browser_download_url"])
        download.raise_for_status()
    digest = hashlib.sha256(download.content).hexdigest()
    if digest != expected:
        raise RuntimeError("GitHub CLI checksum mismatch")
    dest = ROOT / ".tools/gh"
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
        for item in archive.infolist():
            target = (dest / item.filename).resolve()
            if not target.is_relative_to(dest.resolve()):
                raise RuntimeError("Unsafe archive path")
        archive.extractall(dest)
    executable = next(dest.rglob("gh.exe"))
    write_json(
        ROOT / "reports/gh_bootstrap.json",
        {
            "version": release["tag_name"],
            "sha256": digest,
            "asset": asset["name"],
            "checksum_verified": True,
            "executable": str(executable.relative_to(ROOT)),
        },
    )
    print(str(executable))


if __name__ == "__main__":
    main()
