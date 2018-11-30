#!/bin/sh

git config core.hookspath $(realpath $(dirname $0))

echo "core.hookspath is set to $(git config core.hookspath)"
