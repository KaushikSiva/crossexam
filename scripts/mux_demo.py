"""Mux the real browser capture, narration and timed captions into a <60s film."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

raw=Path('recordings/raw/crossexam-capture.webm')
timing=json.loads(Path('recordings/capture-timing.json').read_text())
if timing.get('timingSha256') != hashlib.sha256(Path('recordings/timing.json').read_bytes()).hexdigest():
    raise SystemExit('Capture belongs to different narration timings; re-record before muxing.')
if timing.get('captureSha256') != hashlib.sha256(raw.read_bytes()).hexdigest():
    raise SystemExit('Capture hash differs from the recording receipt; re-record before muxing.')
duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(raw)],text=True))
if not timing.get('syncMarker'):raise SystemExit('Re-record with an explicit synchronization marker.')
rate=Fraction(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=r_frame_rate','-of','default=noprint_wrappers=1:nokey=1',str(raw)],text=True).strip())
pixels=subprocess.check_output(['ffmpeg','-v','error','-i',str(raw),'-vf','crop=2:2:0:0,format=rgb24','-f','rawvideo','-'])
markers=[i//12 for i in range(0,len(pixels),12) if pixels[i]<60 and pixels[i+1]>190 and pixels[i+2]<80]
if len(markers)<3:raise SystemExit('Synchronization marker missing; refusing to guess audio alignment.')
prefix=float(Fraction(markers[-1]+1)/rate)
output=Path('docs/assets/crossexam-demo.mp4')
voice_seconds=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1','recordings/narration.wav'],text=True))
film_seconds=round(min(59.7,max(50,voice_seconds+2)),1)
style='FontName=Arial,FontSize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00111111,BorderStyle=3,Outline=1,Shadow=0,MarginV=14'
subprocess.run(['ffmpeg','-y','-loglevel','warning','-ss',str(prefix),'-i',str(raw),'-i','recordings/narration.wav',
                '-map','0:v:0','-map','1:a:0','-vf',f"tpad=stop_mode=clone:stop_duration=3,subtitles=recordings/demo.srt:force_style='{style}'",
                '-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-r','30',
                '-c:a','aac','-b:a','160k','-af','apad','-movflags','+faststart','-t',str(film_seconds),str(output)],check=True)
info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)],text=True))
assert 50<=float(info['format']['duration'])<=60
assert any(s['codec_type']=='audio' for s in info['streams'])
assert any(s['codec_type']=='video' and s['width']==1600 and s['height']==900 for s in info['streams'])
metadata={'file':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
          'duration_seconds':float(info['format']['duration']),'resolution':[1600,900],
          'captions':'burned in and available as demo.vtt','narration':'See narration-provenance.json',
          'capture':'Actual browser interactions; saved benchmark results, not a fresh model run during recording.'}
Path('docs/assets/demo-provenance.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps(metadata,indent=2))
