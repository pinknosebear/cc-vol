#!/bin/bash
set -e

TEST_VOL="/tmp/test-wabridge-vol"
rm -rf "$TEST_VOL"
mkdir -p "$TEST_VOL"

# Start wa-bridge with custom volume path
export RAILWAY_VOLUME_MOUNT_PATH="$TEST_VOL"
export PORT=3999

cd /Users/bearpot/projects/cc-vol--p4-07/wa-bridge
node index.js &
PID=$!

# Wait for startup
sleep 5

# Check health endpoint
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3999/health)

# Check auth_info was created in volume path
if [ -d "$TEST_VOL/auth_info" ]; then
  echo "PASS: auth_info created at $TEST_VOL/auth_info"
else
  echo "FAIL: auth_info NOT found at $TEST_VOL/auth_info"
  kill $PID 2>/dev/null || true
  rm -rf "$TEST_VOL"
  exit 1
fi

if [ "$STATUS" = "200" ]; then
  echo "PASS: health endpoint returned 200"
else
  echo "FAIL: health endpoint returned $STATUS"
  kill $PID 2>/dev/null || true
  rm -rf "$TEST_VOL"
  exit 1
fi

# Cleanup
kill $PID 2>/dev/null || true
rm -rf "$TEST_VOL"
echo "All tests passed!"
