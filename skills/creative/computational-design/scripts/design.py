"""Simple polygon extrusion and dimensioned multi-component organiser geometry."""
import argparse
import hashlib
import html
import json
import math
import re
from pathlib import Path

SCALE={'mm':1,'cm':10,'m':1000,'in':25.4}
def num(v,name):
    if isinstance(v,bool) or not isinstance(v,(int,float)): raise ValueError(name+' must be numeric')
    try: v=float(v)
    except OverflowError: raise ValueError(name+' too large') from None
    if not math.isfinite(v) or abs(v)>1e8: raise ValueError(name+' outside finite geometry bounds')
    return v
def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def area(p): return math.fsum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))/2
def on(a,b,c,eps): return abs(cross(a,b,c))<=eps and min(a[0],b[0])-eps<=c[0]<=max(a[0],b[0])+eps and min(a[1],b[1])-eps<=c[1]<=max(a[1],b[1])+eps
def intersects(a,b,c,d,eps):
    aa,bb,cc,dd=cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
    return ((aa>eps and bb<-eps or aa<-eps and bb>eps) and (cc>eps and dd<-eps or cc<-eps and dd>eps)) or on(a,b,c,eps) or on(a,b,d,eps) or on(c,d,a,eps) or on(c,d,b,eps)
def validate_polygon(p,minimum=0):
    n=len(p)
    if not 3<=n<=200: raise ValueError('polygon needs 3..200 vertices')
    extent=max(max(x for x,y in p)-min(x for x,y in p),max(y for x,y in p)-min(y for x,y in p),1)
    eps=1e-10*extent*extent
    for i in range(n):
        if math.dist(p[i],p[(i+1)%n])<=max(1e-9,minimum-1e-9): raise ValueError('edge duplicate or below minimum')
        for j in range(i+1,n):
            if j==i+1 or (i==0 and j==n-1): continue
            if intersects(p[i],p[(i+1)%n],p[j],p[(j+1)%n],eps): raise ValueError('polygon self-intersects or self-touches')
    ar=area(p)
    if abs(ar)<=eps: raise ValueError('zero or ill-conditioned polygon area')
    return p if ar>0 else list(reversed(p))
def triangulate(p):
    active=list(range(len(p))); triangles=[]; eps=1e-10*max(1,abs(area(p)))
    while len(active)>3:
        found=False
        for k,i in enumerate(active):
            a=active[k-1]; b=i; c=active[(k+1)%len(active)]
            if cross(p[a],p[b],p[c])<=eps: continue
            if any(cross(p[a],p[b],p[j])>=-eps and cross(p[b],p[c],p[j])>=-eps and cross(p[c],p[a],p[j])>=-eps for j in active if j not in (a,b,c)): continue
            triangles.append((a,b,c)); del active[k]; found=True; break
        if not found: raise ValueError('triangulation failed; collinear/ill-conditioned vertices unsupported')
    triangles.append(tuple(active))
    if abs(math.fsum(cross(p[a],p[b],p[c])/2 for a,b,c in triangles)-area(p))>1e-8*max(1,area(p)): raise ValueError('triangulation area mismatch')
    return triangles
def extrude(name,p,z,height):
    p=validate_polygon(p); cap=triangulate(p); n=len(p)
    vertices=[(x,y,z) for x,y in p]+[(x,y,z+height) for x,y in p]
    faces=[(c,b,a) for a,b,c in cap]+[(a+n,b+n,c+n) for a,b,c in cap]
    for i in range(n):
        j=(i+1)%n; faces.extend([(i,j,j+n),(i,j+n,i+n)])
    edge={}; signed=0
    for a,b,c in faces:
        aa,bb,cc=vertices[a],vertices[b],vertices[c]
        u=[bb[i]-aa[i] for i in range(3)]; v=[cc[i]-aa[i] for i in range(3)]
        cr=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        if math.sqrt(sum(q*q for q in cr))<=1e-12: raise ValueError('degenerate mesh triangle')
        signed+=(aa[0]*(bb[1]*cc[2]-bb[2]*cc[1])+aa[1]*(bb[2]*cc[0]-bb[0]*cc[2])+aa[2]*(bb[0]*cc[1]-bb[1]*cc[0]))/6
        for e in ((a,b),(b,c),(c,a)): edge.setdefault(tuple(sorted(e)),[]).append(e)
    if any(len(es)!=2 or es[0]!=(es[1][1],es[1][0]) for es in edge.values()): raise ValueError('mesh component not oriented closed')
    expected=area(p)*height
    if abs(signed-expected)>1e-7*max(1,expected): raise ValueError('mesh signed volume mismatch')
    return {'name':name,'polygon':p,'vertices':vertices,'faces':faces,'area_mm2':area(p),'perimeter_mm':sum(math.dist(p[i],p[(i+1)%n]) for i in range(n)),'volume_mm3':signed,'closed_oriented_component':True}
def build(d):
    if not isinstance(d,dict) or type(d.get('schema')) is not int or d.get('schema')!=1 or d.get('unit') not in SCALE: raise ValueError('schema 1 and supported unit required')
    scale=SCALE[d['unit']]; accent=d.get('accent','#b6603c')
    if not isinstance(accent,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',accent): raise ValueError('accent must be six-digit hex')
    def dim(k):
        v=num(d.get(k),k)*scale
        if not 1e-6<v<=1e8: raise ValueError(k+' must be positive bounded dimension')
        return v
    if d.get('kind')=='polygon':
        points=d.get('points')
        if not isinstance(points,list): raise ValueError('points list required')
        p=[]
        for q in points:
            if not isinstance(q,list) or len(q)!=2: raise ValueError('point must have x/y')
            p.append(tuple(num(x,'coordinate')*scale for x in q))
        min_edge=num(d.get('minimum_edge',0),'minimum_edge')*scale
        if min_edge<0: raise ValueError('negative minimum edge')
        p=validate_polygon(p,min_edge); parts=[extrude('polygon',p,0,dim('height'))]
    elif d.get('kind')=='organiser':
        w,dep,h,wall=map(dim,('width','depth','height','wall')); mw,ms=map(dim,('minimum_wall','minimum_slot_width')); n=d.get('slots')
        if type(n) is not int or not 1<=n<=100: raise ValueError('slots needs integer 1..100')
        clear=(w-(n+1)*wall)/n
        if w<=2*wall or dep<=2*wall or h<=wall or wall<mw or clear<ms: raise ValueError('wall, height or slot clearance constraint failed')
        def box(name,x,y,bw,bd,z,bh): return extrude(name,[(x,y),(x+bw,y),(x+bw,y+bd),(x,y+bd)],z,bh)
        parts=[box('floor',0,0,w,dep,0,wall),box('front',0,0,w,wall,wall,h-wall),box('back',0,dep-wall,w,wall,wall,h-wall),box('left',0,wall,wall,dep-2*wall,wall,h-wall),box('right',w-wall,wall,wall,dep-2*wall,wall,h-wall)]
        for i in range(1,n): parts.append(box('divider-'+str(i),wall+i*clear+(i-1)*wall,wall,wall,dep-2*wall,wall,h-wall))
    else: raise ValueError('unsupported kind')
    vertices=[v for part in parts for v in part['vertices']]
    bounds=[[min(v[i] for v in vertices),max(v[i] for v in vertices)] for i in range(3)]
    return parts,bounds,accent
def render_svg(parts,bounds,accent):
    x0,x1=bounds[0]; y0,y1=bounds[1]; width=x1-x0; depth=y1-y0; pad=max(width,depth)*.12+4
    view=f'{x0-pad:g} {y0-pad:g} {width+2*pad:g} {depth+2*pad:g}'
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" role="img" aria-label="Dimensioned geometric design in millimetres"><rect x="{x0-pad}" y="{y0-pad}" width="{width+2*pad}" height="{depth+2*pad}" fill="#faf3e7"/>']
    for part in parts:
        points=' '.join(f'{x:g},{y:g}' for x,y in part['polygon']); opacity='.15' if part['name']=='floor' else '.55'
        out.append(f'<polygon points="{points}" fill="{accent}" fill-opacity="{opacity}" stroke="#4a382b" stroke-width="{max(width,depth)*.003:g}"><title>{html.escape(part["name"])}</title></polygon>')
    fs=max(width,depth)*.035
    out.append(f'<text x="{x0:g}" y="{y1+pad*.65:g}" font-family="sans-serif" font-size="{fs:g}" fill="#4a382b">{width:g} × {depth:g} mm; height {bounds[2][1]-bounds[2][0]:g} mm</text></svg>')
    return ''.join(out)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input'); ap.add_argument('--out-dir',required=True); a=ap.parse_args()
    try:
        raw=Path(a.input).read_bytes()
        if len(raw)>2*1024*1024: raise ValueError('input exceeds 2 MiB')
        d=json.loads(raw); parts,bounds,accent=build(d); svg=render_svg(parts,bounds,accent); obj=['# Millimetres; separately closed component groups']; offset=1
        for part in parts:
            obj.append('g '+part['name']); obj.extend('v '+' '.join(format(x,'.15g') for x in v) for v in part['vertices']); obj.extend('f '+' '.join(str(i+offset) for i in f) for f in part['faces']); offset+=len(part['vertices'])
        receipt={'schema':1,'input_sha256':hashlib.sha256(raw).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'units':'mm','bounds_mm':bounds,'component_volume_sum_mm3':sum(p['volume_mm3'] for p in parts),'components':[{k:v for k,v in p.items() if k not in ('vertices','faces','polygon')} for p in parts],'assembly_is_boolean_union':False,'manufacturing_validated':False}
        out=Path(a.out_dir); out.mkdir(parents=False,exist_ok=False)
        for name,content in [('design.svg',svg),('design.obj','\n'.join(obj)+'\n'),('input.json',json.dumps(d,indent=2,allow_nan=False)),('receipt.json',json.dumps(receipt,indent=2,allow_nan=False))]:
            with (out/name).open('x',encoding='utf-8') as f:f.write(content)
    except (OSError,ValueError,TypeError,OverflowError,ZeroDivisionError) as e: ap.exit(2,'ERROR: '+str(e)+'\n')
if __name__=='__main__': main()
