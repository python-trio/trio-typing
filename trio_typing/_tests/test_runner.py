import os
import sys

from mypy import build
from mypy.modulefinder import BuildSource
from mypy.options import Options
from mypy.test.config import test_temp_dir
from mypy.test.data import DataDrivenTestCase, DataSuite
from mypy.test.helpers import assert_string_arrays_equal


class TrioTestSuite(DataSuite):
    data_prefix = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "test-data"
    )
    files = [name for name in os.listdir(data_prefix) if name.endswith(".test")]
    native_sep = True

    def run_case(self, testcase: DataDrivenTestCase) -> None:
        src = "\n".join(testcase.input)
        options = Options()
        options.show_traceback = True
        options.python_version = sys.version_info[:2]
        options.plugins = ["trio_typing.plugin"]
        # must specify something for config_file, else the plugins don't get loaded
        options.config_file = "/dev/null"
        result = build.build(sources=[BuildSource('main', None, src)], options=options)
        assert_string_arrays_equal(
            testcase.output,
            result.errors,
            f"Unexpected output from {testcase.file} line {testcase.line}"
        )
