#!/bin/bash -ex

WORKSPACE=$(dirname $(readlink -f $0))
cd "$WORKSPACE"

if [ ! -d "COVID-19" ]; then
  git clone https://github.com/CSSEGISandData/COVID-19
fi

cd "COVID-19"
git checkout master
git reset --hard
git pull origin master

git apply "$WORKSPACE/0001-Fix-errors-and-inconsistencies-in-JHU-data.patch"
