"""Generate the requested David Castlemore / Eleven v4 narration.

Reads ELEVENLABS_API_KEY only from the environment or gitignored .env.
Caches the audio by script, voice and model hash to avoid duplicate charges.
Requires ffmpeg/ffprobe. Does not substitute a different voice or model.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

root=Path(__file__).resolve().parent.parent
os.chdir(root)
key=os.environ.get('ELEVENLABS_API_KEY')
if not key and Path('.env').exists():
    for line in Path('.env').read_text().splitlines():
        if line.startswith('ELEVENLABS_API_KEY='):key=line.split('=',1)[1].strip().strip('\"\'')
if not key:raise SystemExit('Set ELEVENLABS_API_KEY in the gitignored .env file.')
voice='XjLkpWUlnhS8i7gGz3lZ'
model='eleven_v4'
segments=json.loads(Path('docs/assets/narration.json').read_text())['segments']
script='\n\n'.join(segments)
payload={'text':script,'model_id':model,'voice_settings':{'stability':.5,'similarity_boost':.8,'speed':1.05}}
fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()+voice.encode()).hexdigest()
folder=Path('recordings/raw');folder.mkdir(parents=True,exist_ok=True)
raw=folder/f'elevenlabs-{fingerprint[:12]}.mp3'
alignment_file=folder/f'elevenlabs-{fingerprint[:12]}.json'
if not(raw.exists() and alignment_file.exists()):
    req=urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128',data=json.dumps(payload).encode(),headers={'xi-api-key':key,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=180) as response:
            result=json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f'ElevenLabs HTTP {exc.code}: '+exc.read().decode()[:700]) from None
    raw.write_bytes(base64.b64decode(result['audio_base64']))
    alignment_file.write_text(json.dumps({k:v for k,v in result.items() if k!='audio_base64'}))
data=json.loads(alignment_file.read_text());alignment=data['alignment']
characters=''.join(alignment['characters'])
starts=alignment['character_start_times_seconds'];ends=alignment['character_end_times_seconds']
duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(raw)],text=True))
speed=max(1,duration/57.5)
if speed>1.2:raise SystemExit(f'Narration is {duration:.1f}s; shorten the script before recording.')
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-af',f'atempo={speed:.8f},loudnorm=I=-16:TP=-1.5:LRA=11','-ar','44100','recordings/narration.wav'],check=True)
scene_starts=[];cursor=0
for segment in segments:
    index=characters.find(segment,cursor)
    if index<0:raise SystemExit('Returned alignment does not match the script; no guessed scene timings will be used.')
    scene_starts.append(starts[index]/speed);cursor=index+len(segment)
scene_starts[0]=0
total=duration/speed
durations=[b-a for a,b in zip(scene_starts,scene_starts[1:]+[total])]
Path('recordings/timing.json').write_text(json.dumps({'durations':durations,'total':total},indent=2))
def stamp(seconds):
    ms=round(seconds*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
captions=[]
for match in re.finditer(r'[^.!?\n]+[.!?]',characters):
    text=match.group().strip()
    first=match.start()+len(match.group())-len(match.group().lstrip())
    captions.append(f'{len(captions)+1}\n{stamp(starts[first]/speed)} --> {stamp(ends[match.end()-1]/speed)}\n{text}\n')
srt='\n'.join(captions)
Path('recordings/demo.srt').write_text(srt)
Path('docs/assets/demo.vtt').write_text('WEBVTT\n\n'+re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})',r'\1.\2',srt))
Path('docs/assets/narration-provenance.json').write_text(json.dumps({'provider':'ElevenLabs','model':model,'voice_name':'David Castlemore - Newsreader and Educator','voice_id':voice,'script_sha256':hashlib.sha256(script.encode()).hexdigest(),'raw_audio_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'raw_seconds':duration,'playback_speed':speed,'final_seconds':total,'synthetic_narration':True},indent=2))
print(f'David Castlemore / {model}: {total:.2f}s, {len(captions)} timed captions. Cached request {fingerprint[:12]}.')
