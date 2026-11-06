#!/usr/bin/env python3
"""Validate a real OBS OpenH264/AAC recording of moving UI and a 440 Hz tone."""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import subprocess


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, timeout=180).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    probe = json.loads(run('ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format',
                           '-of', 'json', str(args.recording)))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    duration = float(probe['format']['duration'])
    if video['codec_name'] != 'h264' or audio['codec_name'] != 'aac' or duration < 5 or int(video['nb_read_frames']) < 30:
        raise SystemExit('Expected at least five seconds of H.264/AAC with 30 decoded frames')
    run('ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(args.recording), '-f', 'null', '-')
    hashes = []
    distinct_values = []
    for second in (1, duration / 2, duration - 1):
        pixels = run('ffmpeg', '-nostdin', '-v', 'error', '-ss', str(second), '-i', str(args.recording),
                     '-frames:v', '1', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-')
        if len(pixels) != video['width'] * video['height'] * 3 or len(set(pixels)) < 16:
            raise SystemExit('Missing or effectively blank video frame')
        hashes.append(hashlib.sha256(pixels).hexdigest())
        distinct_values.append(len(set(pixels)))
    if len(set(hashes)) < 2:
        raise SystemExit('No change between sampled video frames')
    samples = array.array('f', run('ffmpeg', '-nostdin', '-v', 'error', '-i', str(args.recording),
                                  '-t', '30', '-map', '0:a:0', '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'))
    if not samples:
        raise SystemExit('No decoded audio')
    rms = math.sqrt(sum(x*x for x in samples) / len(samples))
    segment = samples[:8*8000]
    real = sum(x * math.cos(2*math.pi*440*i/8000) for i, x in enumerate(segment))
    imag = sum(x * math.sin(2*math.pi*440*i/8000) for i, x in enumerate(segment))
    tone_amplitude = 2 * math.hypot(real, imag) / len(segment)
    if rms < 0.001 or tone_amplitude < 0.001:
        raise SystemExit(f'Expected audible synthetic 440 Hz tone: RMS={rms}, amplitude={tone_amplitude}')
    run('ffmpeg', '-nostdin', '-v', 'error', '-ss', '5', '-i', str(args.recording), '-frames:v', '1',
        '-y', str(args.output_dir / 'decoded-frame.png'))
    with args.recording.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    result = {'status': 'passed', 'duration_seconds': duration, 'video': {
        'codec': video['codec_name'], 'width': video['width'], 'height': video['height'],
        'frame_rate': video['r_frame_rate'], 'decoded_frames': int(video['nb_read_frames']),
        'sample_sha256': hashes, 'sample_distinct_byte_values': distinct_values},
        'audio': {'codec': audio['codec_name'], 'rms': rms, 'tone_440hz_amplitude': tone_amplitude},
        'recording_sha256': digest}
    (args.output_dir / 'recording-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
