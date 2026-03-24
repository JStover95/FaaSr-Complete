"""Compose FaaSr stub mocks for block tests."""

from __future__ import annotations

import tempfile
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator

from faasr_blocks.testing.mocks import (
    MockFaaSrDeleteFile,
    MockFaaSrExit,
    MockFaaSrGetFile,
    MockFaaSrGetFolderList,
    MockFaaSrGetS3Creds,
    MockFaaSrInvocationId,
    MockFaaSrLog,
    MockFaaSrPutFile,
    MockFaaSrRank,
    MockFaaSrReturn,
    MockFaaSrSecret,
)


def _patch_target(module_qualname: str, attr: str) -> str:
    return f"{module_qualname}.{attr}"


@contextmanager
def faasr_test_environment(
    fixtures_dir: Path,
    module_qualname: str,
) -> Iterator[dict[str, Any]]:
    """
    Activate mocks for all FaaSr client stubs used by ``module_qualname``.

    Args:
        fixtures_dir: Directory for :class:`MockFaaSrGetFile` fixture files.
        module_qualname: Import name of the block module under test
            (e.g. ``get_weather_data`` when ``src`` is on ``sys.path``).

    Yields:
        Dict with mock instances and ``output_dir`` (temporary upload root).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        with ExitStack() as stack:
            get_file = stack.enter_context(
                MockFaaSrGetFile(_patch_target(module_qualname, "faasr_get_file"), fixtures_dir)
            )
            put_file = stack.enter_context(
                MockFaaSrPutFile(_patch_target(module_qualname, "faasr_put_file"), output_dir)
            )
            delete_file = stack.enter_context(
                MockFaaSrDeleteFile(_patch_target(module_qualname, "faasr_delete_file"))
            )
            log = stack.enter_context(MockFaaSrLog(_patch_target(module_qualname, "faasr_log")))
            get_folder_list = stack.enter_context(
                MockFaaSrGetFolderList(_patch_target(module_qualname, "faasr_get_folder_list"))
            )
            rank = stack.enter_context(MockFaaSrRank(_patch_target(module_qualname, "faasr_rank")))
            get_s3_creds = stack.enter_context(
                MockFaaSrGetS3Creds(_patch_target(module_qualname, "faasr_get_s3_creds"))
            )
            secret = stack.enter_context(
                MockFaaSrSecret(_patch_target(module_qualname, "faasr_secret"))
            )
            invocation_id = stack.enter_context(
                MockFaaSrInvocationId(_patch_target(module_qualname, "faasr_invocation_id"))
            )
            ret = stack.enter_context(
                MockFaaSrReturn(_patch_target(module_qualname, "faasr_return"))
            )
            exit_mock = stack.enter_context(
                MockFaaSrExit(_patch_target(module_qualname, "faasr_exit"))
            )
            yield {
                "get_file": get_file,
                "put_file": put_file,
                "delete_file": delete_file,
                "log": log,
                "get_folder_list": get_folder_list,
                "rank": rank,
                "get_s3_creds": get_s3_creds,
                "secret": secret,
                "invocation_id": invocation_id,
                "return": ret,
                "exit": exit_mock,
                "output_dir": output_dir,
            }
