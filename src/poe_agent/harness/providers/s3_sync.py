# ROLE: harness — optional S3 sync for raw docs, chunks, and eval logs.

from __future__ import annotations

from pathlib import Path

from poe_agent.harness.config import get_settings


def sync_directory_to_s3(local_dir: Path, subprefix: str = "") -> int:
    settings = get_settings()
    if not settings.s3_bucket:
        return 0

    import boto3

    s3 = boto3.client("s3", region_name=settings.aws_region)
    prefix = f"{settings.s3_prefix.rstrip('/')}/{subprefix}".strip("/")
    uploaded = 0
    if not local_dir.exists():
        return 0
    for path in local_dir.rglob("*"):
        if path.is_file():
            key = f"{prefix}/{path.relative_to(local_dir).as_posix()}"
            s3.upload_file(str(path), settings.s3_bucket, key)
            uploaded += 1
    return uploaded


def sync_data_to_s3() -> dict[str, int]:
    settings = get_settings()
    return {
        "raw": sync_directory_to_s3(settings.raw_dir, "raw"),
        "chunks": sync_directory_to_s3(settings.chunks_dir, "chunks"),
        "eval": sync_directory_to_s3(settings.eval_dir, "eval"),
    }
