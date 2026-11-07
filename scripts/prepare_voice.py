"""macOS narration. Individual measured segment durations drive the recording."""

import json
from pathlib import Path
import subprocess

data=json.loads(Path('docs/assets/narration.json').read_text())
folder=Path('recordings');folder.mkdir(exist_ok=True)
durations=[]
for i,segment in enumerate(data['segments']):
    text=folder/f'segment-{i}.txt';text.write_text(segment)
    output=folder/f'segment-{i}.aiff'
    subprocess.run(['say','-v','Samantha','-r','187','-f',str(text),'-o',str(output)],check=True)
    info=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(output)],text=True)
    durations.append(float(info)+.15)
# Normalize narration to fit a 58-second scene budget. Browser navigation adds
# a small overhead; the final mux trims to <=60s after checking the capture.
speed=max(1,sum(durations)/57.5)
durations=[d/speed for d in durations]
inputs=[]
for i in range(len(durations)):inputs += ['-i',str(folder/f'segment-{i}.aiff')]
filters=';'.join(f'[{i}:a]atempo={speed:.6f},apad=pad_dur={.15/speed:.6f}[a{i}]' for i in range(len(durations)))
filters+=';'+''.join(f'[a{i}]' for i in range(len(durations)))+f'concat=n={len(durations)}:v=0:a=1[out]'
subprocess.run(['ffmpeg','-y','-loglevel','error',*inputs,'-filter_complex',filters,'-map','[out]',str(folder/'narration.wav')],check=True)
(folder/'timing.json').write_text(json.dumps({'durations':durations,'total':sum(durations)},indent=2))
def timestamp(seconds):
    ms=round(seconds*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
start=0;captions=[]
for i,(segment,duration) in enumerate(zip(data['segments'],durations)):
    # Sentence-level subtitles remain readable instead of displaying a paragraph.
    sentences=[s.strip()+'.' for s in segment.split('.') if s.strip()]
    weights=[len(s.split()) for s in sentences];total=sum(weights)
    for sentence,weight in zip(sentences,weights):
        end=start+duration*weight/total
        captions.append(f'{len(captions)+1}\n{timestamp(start)} --> {timestamp(end)}\n{sentence}\n')
        start=end
(folder/'demo.srt').write_text('\n'.join(captions))
print(f'Narration ready: {sum(durations):.2f}s. Synthetic Samantha voice; no voice cloning.')
