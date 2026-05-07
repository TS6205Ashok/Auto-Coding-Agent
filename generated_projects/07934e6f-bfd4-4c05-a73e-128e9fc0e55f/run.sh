#!/usr/bin/env bash
set -e
(cd backend && mvn spring-boot:run) &
(cd frontend && npm run dev) &
wait
