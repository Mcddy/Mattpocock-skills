"""Typed declarative scenes, rational time and deterministic SVG/PNG rendering."""
import argparse
from fractions import Fraction
import hashlib
import html
import json
import math
import re
import struct
import zlib
from pathlib import Path

def num(v,label='number'):
    if isinstance(v,bool) or not isinstance(v,(int,float)): raise ValueError(label+' must be numeric')
    try:v=float(v)
    except OverflowError:raise ValueError(label+' too large') from None
    if not math.isfinite(v) or abs(v)>1e9:raise ValueError(label+' outside finite range')
    return v
def rational(v):
    if isinstance(v,bool) or not isinstance(v,(str,int,float)):raise ValueError('time must be rational string or number')
    if isinstance(v,str) and (len(v)>50 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+|/[0-9]+)?',v)):raise ValueError('bad rational time')
    if isinstance(v,float):num(v,'time')
    try:q=Fraction(str(v))
    except (ValueError,ZeroDivisionError):raise ValueError('bad rational time') from None
    if abs(q)>10000 or q.denominator>1000000000:raise ValueError('time outside bounds')
    return q
def colour(c):
    if not isinstance(c,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',c):raise ValueError('colour must be #RRGGBB')
    return c
def text(v,n):
    if not isinstance(v,str) or len(v)>n:raise ValueError('bounded text required')
    if any(not (ord(c) in (9,10,13) or 32<=ord(c)<=0xD7FF or 0xE000<=ord(c)<=0xFFFD or 0x10000<=ord(c)<=0x10FFFF) for c in v):raise ValueError('text contains an XML-forbidden character; preserve the original input and use a supported representation')
    return v
def value(v,t,data):
    if not isinstance(v,dict):return num(v)
    if 'data' in v:
        if set(v)-{'data','index','scale','offset'}:raise ValueError('unknown data binding field')
        name=v['data']; i=v.get('index')
        if not isinstance(name,str) or name not in data or type(i) is not int or not 0<=i<len(data[name]):raise ValueError('unresolved data binding')
        return num(data[name][i]*num(v.get('scale',1))+num(v.get('offset',0)))
    if 'keys' in v:
        if set(v)-{'keys','easing'}:raise ValueError('unknown keyframe field')
        keys=v['keys']; easing=v.get('easing','linear')
        if not isinstance(keys,list) or not 1<=len(keys)<=1000 or easing not in ('linear','step','smooth'):raise ValueError('invalid keyframes')
        pairs=[]
        for k in keys:
            if not isinstance(k,list) or len(k)!=2:raise ValueError('keyframe must have time/value')
            tt=rational(k[0]); vv=num(k[1])
            if tt<0 or (pairs and tt<=pairs[-1][0]):raise ValueError('keyframes must increase')
            pairs.append((tt,vv))
        if t<=pairs[0][0]:return pairs[0][1]
        if t>=pairs[-1][0]:return pairs[-1][1]
        for (a,x),(b,y) in zip(pairs,pairs[1:]):
            if a<=t<b:
                u=float((t-a)/(b-a)); u=0 if easing=='step' else (u*u*(3-2*u) if easing=='smooth' else u)
                return num(x+(y-x)*u)
    if 'function' in v:
        if set(v)-{'function','frequency','phase','amplitude','offset'} or v['function'] not in ('sin','cos'):raise ValueError('unsupported procedural function')
        fn=math.sin if v['function']=='sin' else math.cos
        return num(num(v.get('offset',0))+num(v.get('amplitude',1))*fn(2*math.pi*num(v.get('frequency',1))*float(t)+num(v.get('phase',0))))
    raise ValueError('unknown numeric binding')

FIELDS={'rect':{'x','y','width','height','fill'},'circle':{'cx','cy','r','fill'},'line':{'x1','y1','x2','y2','stroke','stroke_width'},'text':{'x','y','text','size','fill'},'group':{'x','y','scale','children'}}
def flatten(nodes,t,data,ids=None,depth=0,tx=0,ty=0,scale=1,counter=None):
    if ids is None:ids=set()
    if counter is None:counter=[0]
    if not isinstance(nodes,list) or depth>8:raise ValueError('invalid scene list/depth')
    out=[]
    for node in nodes:
        if not isinstance(node,dict):raise ValueError('node must be object')
        kind=node.get('type'); ident=node.get('id')
        if kind not in FIELDS or not isinstance(ident,str) or not 1<=len(ident)<=100 or ident in ids:raise ValueError('node type/unique id invalid')
        if set(node)-({'type','id'}|FIELDS[kind]):raise ValueError('unknown node field')
        ids.add(ident);counter[0]+=1
        if counter[0]>200:raise ValueError('node budget exceeded')
        if kind=='group':
            x=value(node.get('x',0),t,data);y=value(node.get('y',0),t,data);s=value(node.get('scale',1),t,data)
            if not 0<s<=100:raise ValueError('group scale must be in (0,100]')
            out.extend(flatten(node.get('children'),t,data,ids,depth+1,tx+x*scale,ty+y*scale,scale*s,counter));continue
        required=FIELDS[kind]
        if not required<=set(node):raise ValueError('missing node fields')
        r={'id':ident,'type':kind}
        for k in sorted(required):
            if k in ('fill','stroke'):r[k]=colour(node[k])
            elif k=='text':r[k]=text(node[k],500)
            else:r[k]=value(node[k],t,data)
        for k in ('x','cx','x1','x2'):
            if k in r:r[k]=num(tx+r[k]*scale)
        for k in ('y','cy','y1','y2'):
            if k in r:r[k]=num(ty+r[k]*scale)
        for k in ('width','height','r','stroke_width','size'):
            if k in r:
                r[k]=num(r[k]*scale)
                if not 0<r[k]<=10000:raise ValueError('shape dimension must be in (0,10000]')
        out.append(r)
    return out
def svg(primitives,w,h,bg,title,time):
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"><title>{html.escape(title)}; t={time}</title><rect width="{w}" height="{h}" fill="{bg}"/>']
    for r in primitives:
        kind=r['type']; attrs=' '.join(f'{("font-size" if k=="size" else k.replace("_","-"))}="{html.escape(format(v,".15g") if isinstance(v,(int,float)) else v,quote=True)}"' for k,v in sorted(r.items()) if k not in ('id','type','text'))
        out.append(f'<text {attrs} font-family="sans-serif">{html.escape(r["text"])}</text>' if kind=='text' else f'<{kind} {attrs}/>')
    return ''.join(out)+'</svg>'
def rgb(c):return bytes(int(c[i:i+2],16) for i in (1,3,5))
def png(primitives,w,h,bg):
    pixels=bytearray(rgb(bg)*(w*h))
    def paint(x,y,c):pixels[(y*w+x)*3:(y*w+x)*3+3]=c
    for r in primitives:
        kind=r['type']
        if kind=='text':raise ValueError('PNG text renderer unsupported; choose SVG or an explicitly reviewed typography adapter')
        c=rgb(r.get('fill',r.get('stroke')))
        if kind=='rect':bounds=(r['x'],r['y'],r['x']+r['width'],r['y']+r['height'])
        elif kind=='circle':bounds=(r['cx']-r['r'],r['cy']-r['r'],r['cx']+r['r'],r['cy']+r['r'])
        else:
            pad=r['stroke_width']/2;bounds=(min(r['x1'],r['x2'])-pad,min(r['y1'],r['y2'])-pad,max(r['x1'],r['x2'])+pad,max(r['y1'],r['y2'])+pad)
        xa=max(0,math.floor(bounds[0]));ya=max(0,math.floor(bounds[1]));xb=min(w,math.ceil(bounds[2]));yb=min(h,math.ceil(bounds[3]))
        for y in range(ya,yb):
            for x in range(xa,xb):
                xx=x+.5;yy=y+.5
                if kind=='rect':inside=r['x']<=xx<r['x']+r['width'] and r['y']<=yy<r['y']+r['height']
                elif kind=='circle':inside=(xx-r['cx'])**2+(yy-r['cy'])**2<=r['r']**2
                else:
                    dx=r['x2']-r['x1'];dy=r['y2']-r['y1'];den=dx*dx+dy*dy
                    u=max(0,min(1,((xx-r['x1'])*dx+(yy-r['y1'])*dy)/den)) if den else 0
                    inside=(xx-r['x1']-u*dx)**2+(yy-r['y1']-u*dy)**2<=(r['stroke_width']/2)**2
                if inside:paint(x,y,c)
    raw=b''.join(b'\0'+bytes(pixels[y*w*3:(y+1)*w*3]) for y in range(h))
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
def compile_scene(d):
    if not isinstance(d,dict) or type(d.get('schema')) is not int or d.get('schema')!=1:raise ValueError('schema 1 required')
    if set(d)-{'schema','title','caption','source','width','height','duration','fps','background','formats','data','scene'}:raise ValueError('unknown scene field')
    w,h=d.get('width'),d.get('height')
    if type(w) is not int or type(h) is not int or not 32<=w<=512 or not 32<=h<=512:raise ValueError('dimensions need integers 32..512')
    title=text(d.get('title'),500);caption=text(d.get('caption'),500);text(d.get('source'),1000)
    duration=rational(d.get('duration'));fps=rational(d.get('fps'))
    if duration<=0 or not 0<fps<=60:raise ValueError('positive duration/fps <=60 required')
    count=math.ceil(duration*fps)
    if count>120 or count*w*h>30000000:raise ValueError('frame/pixel budget exceeded')
    formats=d.get('formats')
    if not isinstance(formats,list) or not formats or len(set(formats))!=len(formats) or any(x not in ('svg','png') for x in formats):raise ValueError('formats must be unique svg/png list')
    data=d.get('data');bg=colour(d.get('background'))
    if not isinstance(data,dict) or sum(len(v) if isinstance(v,list) else 10001 for v in data.values())>10000:raise ValueError('bounded numeric data object required')
    for k,v in data.items():
        if not isinstance(k,str) or not k or not isinstance(v,list):raise ValueError('data series malformed')
        for x in v:num(x)
    first=flatten(d.get('scene'),Fraction(0),data)
    if count*w*h*max(1,len(first))>60000000:raise ValueError('primitive raster work budget exceeded')
    frames=[]
    for i in range(count):
        t=Fraction(i,1)/fps;p=flatten(d.get('scene'),t,data)
        if 'png' in formats and any(r['type']=='text' for r in p):raise ValueError('PNG text unsupported; select SVG')
        frames.append({'index':i,'time':str(t),'primitives':p,'svg':svg(p,w,h,bg,title,t),'png':png(p,w,h,bg) if 'png' in formats else None})
    return frames
def preview(d,frames):
    payload=json.dumps({'frames':[f['svg'] for f in frames]},ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'''+html.escape(d['title'])+'''</title><style>body{margin:auto;padding:24px;max-width:740px;background:#faf3e7;color:#49392c;font:17px system-ui}body.dark{background:#241e1a;color:#f5eadb}button,select,input{font:inherit;padding:8px;margin:5px;border:1px solid #a38c74;border-radius:6px;background:#f4e5cf;color:#49392c}#frame svg{width:100%;height:auto;max-height:65vh}#scrub{width:90%}#error{color:#b34b35}</style><h1>'''+html.escape(d['title'])+'''</h1><p>'''+html.escape(d['caption'])+'''</p><p>Source: '''+html.escape(d['source'])+'''</p><label>Appearance <select id="theme"><option value="warm">Warm</option><option value="dark">Dark</option></select></label><div id="frame"></div><label>Frame <input id="scrub" type="range" min="0" max="'''+str(len(frames)-1)+'''" value="0"><output id="position"></output></label><p><button id="svgExport">Export this SVG</button><button id="stateExport">Export preview state</button><label>Reopen state <input id="stateImport" type="file" accept="application/json,.json"></label></p><p id="error" role="alert"></p><script>const data='''+payload+''';const frame=document.getElementById('frame'),scrub=document.getElementById('scrub'),theme=document.getElementById('theme'),error=document.getElementById('error');function show(){frame.innerHTML=data.frames[Number(scrub.value)];document.getElementById('position').textContent=(Number(scrub.value)+1)+' / '+data.frames.length;document.body.classList.toggle('dark',theme.value==='dark')}function save(name,text,type){let a=document.createElement('a'),u=URL.createObjectURL(new Blob([text],{type}));a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}scrub.addEventListener('input',show);theme.addEventListener('change',show);document.getElementById('svgExport').onclick=()=>save('selected-frame.svg',data.frames[Number(scrub.value)],'image/svg+xml');document.getElementById('stateExport').onclick=()=>save('preview-state.json',JSON.stringify({schema:1,index:Number(scrub.value),theme:theme.value}),'application/json');document.getElementById('stateImport').onchange=async e=>{try{let f=e.target.files[0];if(!f||f.size>4096)throw Error('Choose a preview state under 4 KiB');let s=JSON.parse(await f.text());if(!s||Object.keys(s).sort().join(',')!=='index,schema,theme'||s.schema!==1||!Number.isInteger(s.index)||s.index<0||s.index>=data.frames.length||!['warm','dark'].includes(s.theme))throw Error('Invalid preview state; current frame preserved');scrub.value=s.index;theme.value=s.theme;error.textContent='';show()}catch(ex){error.textContent=ex.message}finally{e.target.value=''}};show();</script></html>'''
def main():
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('--out-dir',required=True);a=ap.parse_args()
    try:
        raw=Path(a.input).read_bytes()
        if len(raw)>2*1024*1024:raise ValueError('input exceeds 2 MiB')
        d=json.loads(raw);frames=compile_scene(d);compiler=Path(__file__).read_bytes();out=Path(a.out_dir);out.mkdir(parents=False,exist_ok=False)
        entries=[]
        for f in frames:
            e={k:f[k] for k in ('index','time','primitives')};e['files']={}
            for fmt in d['formats']:
                payload=f['svg'].encode('utf-8') if fmt=='svg' else f['png'];name=f'frame-{f["index"]:04d}.{fmt}'
                with (out/name).open('xb') as file:file.write(payload)
                e['files'][fmt]={'path':name,'sha256':hashlib.sha256(payload).hexdigest()}
            entries.append(e)
        manifest={'schema':1,'source':d['source'],'synthetic':d['source'].lower().startswith('synthetic'),'input_sha256':hashlib.sha256(raw).hexdigest(),'compiler_sha256':hashlib.sha256(compiler).hexdigest(),'dependency_sha256':hashlib.sha256(raw+compiler).hexdigest(),'fps':str(rational(d['fps'])),'duration':str(rational(d['duration'])),'frame_count':len(frames),'frames':entries,'png_typography_supported':False,'video_encoded':False}
        for name,content in [('scene.json',json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)),('manifest.json',json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False)),('preview.html',preview(d,frames))]:
            with (out/name).open('x',encoding='utf-8') as file:file.write(content)
    except (OSError,ValueError,TypeError,OverflowError,ZeroDivisionError) as e:ap.exit(2,'ERROR: '+str(e)+'\n')
if __name__=='__main__':main()
