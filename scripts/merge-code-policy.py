#!/usr/bin/env python3
"""Generate a telemetry policy while preserving unrelated enterprise policies."""
import json
from pathlib import Path
import sys
source, destination = map(Path, sys.argv[1:])
policy = json.loads(source.read_text()) if source.exists() else {}
if not isinstance(policy, dict):
    raise ValueError('VS Code policy must be a JSON object')
policy['TelemetryLevel'] = 'off'
policy['EnableFeedback'] = False
destination.write_text(json.dumps(policy, indent=2)+'\n')
