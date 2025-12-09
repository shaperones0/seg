#!/bin/sh

set -e

python -m seg.main --verbose

python -m seg.app
