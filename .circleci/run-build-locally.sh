#!/usr/bin/env bash
curl -v \
    --request POST \
    --form config=@config.yml \
    --form notify=false \
    https://circleci.com/api/v1.1/project/github/CodeForLancaster/sitegeist/?circle-token=2416410a18ad2d292a0614e9a88221faf0517ebd
