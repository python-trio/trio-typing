#!/bin/bash

set -ex -o pipefail

BLACK_VERSION=22.3
MYPY_VERSION=1.4

pip install -U pip setuptools wheel

if [ "$CHECK_FORMATTING" = "1" ]; then
    pip install black==${BLACK_VERSION}
    if ! black --check setup.py async_generator-stubs outcome-stubs trio-stubs trio_typing; then
        cat <<EOF
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Formatting problems were found (listed above). To fix them, run

   pip install black==${BLACK_VERSION}
   black setup.py async_generator-stubs outcome-stubs trio-stubs trio_typing

in your local checkout.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
EOF
        exit 1
    fi
    exit 0
fi

if [ "$CHECK_TYPING" = "1" ]; then
    pip install mypy==${MYPY_VERSION}
    pip install -Ur test-requirements.txt
    mkdir empty; cd empty
    ln -s ../async_generator-stubs async_generator
    ln -s ../outcome-stubs outcome
    ln -s ../trio-stubs trio
    ln -s ../trio_typing trio_typing
    mypy --strict -p async_generator -p outcome -p trio -m trio_typing -m trio_typing.plugin
    exit $?
fi

python setup.py sdist --formats=zip
pip install dist/*.zip

if [ "$CHECK_STUBS" = "1" ]; then
    pip install mypy==${MYPY_VERSION}
    mkdir empty; cd empty
    ln -s ../async_generator-stubs async_generator
    ln -s ../outcome-stubs outcome
    ln -s ../trio-stubs trio
    ln -s ../trio_typing trio_typing
    python -m mypy.stubtest --allowlist=../allowlist.txt --ignore-unused-allowlist trio
    exit $?
fi

# Actual tests
pip install -Ur test-requirements.txt

mkdir empty
cd empty

# The data-driven tests import mypy.build, which imports
# distutils. On Travis this apparently imports imp and triggers
# a deprecation warning.
if [ "$RUNTIME_ONLY" = "1" ]; then
    pytest -W error -W ignore:::distutils -ra -v --pyargs trio_typing -k test_runtime
else
    pip install mypy==${MYPY_VERSION}
    pytest -W error -W ignore:::distutils -ra -v -p trio_typing._tests.datadriven --pyargs trio_typing
fi

