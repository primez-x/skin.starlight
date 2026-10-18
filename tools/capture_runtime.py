"""Capture the cleared Living Room Kodi GUI without screenshot animation loss.

SSHPASS must contain the SSH password. The device address is fixed for safety.
Run: python3 tools/capture_runtime.py /tmp/starlight-runtime/home-landing.png
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageStat

HOST = 'root@192.168.0.31'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
args = parser.parse_args()
# Snapshot on the device before network transfer to prevent partial redraws.
subprocess.run(['sshpass', '-e', 'ssh', HOST,
                'dd if=/dev/fb0 of=/tmp/starlight-fb.raw bs=16588800 count=1 2>/dev/null'], check=True)
with tempfile.TemporaryDirectory(prefix='starlight-fb-') as scratch:
    path = Path(scratch) / 'fb.raw'
    subprocess.run(['sshpass', '-e', 'scp', HOST + ':/tmp/starlight-fb.raw', str(path)], check=True)
    data = path.read_bytes()
page_size = 1920 * 1080 * 4
if len(data) != 2 * page_size:
    raise RuntimeError('The framebuffer dimensions changed')
frames = [Image.frombytes('RGBA', (1920, 1080), data[n:n + page_size], 'raw', 'BGRA').convert('RGB')
          for n in (0, page_size)]
args.output.parent.mkdir(parents=True, exist_ok=True)
max(frames, key=lambda frame: ImageStat.Stat(frame.convert('L')).mean[0]).save(args.output)
print(args.output)
