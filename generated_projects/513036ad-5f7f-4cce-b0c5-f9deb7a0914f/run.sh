#!/usr/bin/env bash
set -e
(cd backend && ./run.sh) &
(cd frontend && npm run dev) &
wait
