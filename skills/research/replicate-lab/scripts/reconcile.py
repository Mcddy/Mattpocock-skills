"""Bounded numerical reconciliation. No evaluated expressions or external imports."""
import argparse
import hashlib
import json
import math
from pathlib import Path

UNITS = {'1':('dimensionless',1,0),'m':('length',1,0),'cm':('length',.01,0),'mm':('length',.001,0),'in':('length',.0254,0),'s':('time',1,0),'ms':('time',.001,0),'min':('time',60,0),'h':('time',3600,0),'kg':('mass',1,0),'g':('mass',.001,0),'K':('temperature',1,0),'C':('temperature',1,273.15)}

def number(v, name):
    if isinstance(v, bool) or not isinstance(v, (int,float)):
        raise ValueError(name+' must be a finite number')
    try: v=float(v)
    except OverflowError: raise ValueError(name+' is too large') from None
    if not math.isfinite(v): raise ValueError(name+' must be finite')
    return v

def unit(name):
    if not isinstance(name,str) or name not in UNITS: raise ValueError('unsupported unit')
    return UNITS[name]

def canonical(v, name):
    _, scale, offset=unit(name)
    return number(number(v,'quantity')*scale+offset,'converted quantity')

def reconcile(d):
    if not isinstance(d,dict) or type(d.get('schema')) is not int or d.get('schema')!=1: raise ValueError('schema must be 1')
    for k in ('implementation',):
        if not isinstance(d.get(k),str) or not d[k].strip(): raise ValueError(k+' required')
    if not isinstance(d.get('source'),dict) or not isinstance(d['source'].get('locator'),str) or not d['source']['locator'].strip(): raise ValueError('source locator required')
    iu,ou=d.get('input_unit'),d.get('output_unit'); unit(iu); od=unit(ou)[0]
    p=d.get('parameters',{}); t=d.get('tolerance')
    if not isinstance(p,dict) or not isinstance(t,dict): raise ValueError('parameters/tolerance objects required')
    absolute=number(t.get('absolute'),'absolute'); relative=number(t.get('relative'),'relative')
    if absolute<0 or relative<0: raise ValueError('negative tolerance')
    norm=number(d.get('normalisation',1),'normalisation')
    if norm<=0: raise ValueError('normalisation must be positive')
    model=d.get('model'); rows=d.get('rows')
    if model not in ('linear','exponential-decay','power-law','normal-pdf','supplied-results'): raise ValueError('unsupported model')
    if not isinstance(rows,list) or not 1<=len(rows)<=10000: raise ValueError('need 1..10000 rows')
    if model=='normal-pdf' and (unit(iu)[0]!='dimensionless' or od!='dimensionless'): raise ValueError('normal-pdf requires dimensionless units')
    seen=set(); results=[]
    for r in rows:
        if not isinstance(r,dict) or not isinstance(r.get('id'),str) or not r['id'] or r['id'] in seen: raise ValueError('unique row id required')
        seen.add(r['id']); x=canonical(r.get('x'),iu)
        if unit(r.get('reported_unit'))[0]!=od: raise ValueError('incompatible output units')
        reported=canonical(r.get('reported'),r['reported_unit'])
        if model=='supplied-results': y=number(r.get('reproduced'),'reproduced')
        elif model=='linear': y=number(p.get('slope'),'slope')*x+number(p.get('intercept'),'intercept')
        elif model=='exponential-decay': y=number(p.get('amplitude'),'amplitude')*math.exp(-number(p.get('rate'),'rate')*x)
        elif model=='power-law':
            if x<=0: raise ValueError('power-law requires positive x')
            y=number(p.get('amplitude'),'amplitude')*x**number(p.get('exponent'),'exponent')
        else:
            sigma=number(p.get('sigma'),'sigma')
            if sigma<=0: raise ValueError('sigma must be positive')
            z=(x-number(p.get('mean'),'mean'))/sigma
            y=math.exp(-.5*z*z)/(sigma*math.sqrt(2*math.pi))
        reproduced=canonical(number(y*norm,'prediction'),ou) if model=='supplied-results' else number(y*norm,'canonical prediction')
        delta=number(abs(reproduced-reported),'difference'); allowed=number(absolute+relative*max(abs(reproduced),abs(reported)),'tolerance')
        results.append({'id':r['id'],'raw':r,'reproduced_canonical':reproduced,'reported_canonical':reported,'absolute_difference':delta,'allowed_difference':allowed,'agrees':delta<=allowed})
    return {'schema':1,'status':'AGREES' if all(r['agrees'] for r in results) else 'DISCREPANCY','model':model,'implementation':d['implementation'],'source':d['source'],'output_dimension':od,'absolute_tolerance_canonical':absolute,'relative_tolerance':relative,'normalisation':norm,'rows':results,'execution_kind':'supplied output comparison' if model=='supplied-results' else 'bundled reference kernel','limitation':'Numeric agreement does not validate the scientific model or provenance.'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input'); ap.add_argument('--out',required=True); a=ap.parse_args()
    try:
        raw=Path(a.input).read_bytes()
        if len(raw)>4*1024*1024: raise ValueError('input exceeds 4 MiB')
        result=reconcile(json.loads(raw)); result['input_sha256']=hashlib.sha256(raw).hexdigest(); result['implementation_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        with Path(a.out).open('x',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    except (ValueError,TypeError,KeyError,OverflowError,OSError) as e: ap.exit(2,'ERROR: '+str(e)+'\n')
if __name__=='__main__': main()
