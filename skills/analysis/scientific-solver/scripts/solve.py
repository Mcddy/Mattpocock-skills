"""Adaptive typed ODE kernels and bounded known-noise likelihood profiles."""
import argparse
import hashlib
import json
import math
from pathlib import Path

def num(x,label):
    if isinstance(x,bool) or not isinstance(x,(int,float)): raise ValueError(label+' must be numeric')
    try: x=float(x)
    except OverflowError: raise ValueError(label+' too large') from None
    if not math.isfinite(x): raise ValueError(label+' must be finite')
    return x
def positive(x,label):
    x=num(x,label)
    if x<=0: raise ValueError(label+' must be positive')
    return x
def integer(x,lo,hi,label):
    if type(x) is not int or not lo<=x<=hi: raise ValueError(label+' outside bounds')
    return x
def label(x):
    if not isinstance(x,str) or not x.strip() or len(x)>100: raise ValueError('unit label required')
    return x
def rk4(y,h,f):
    k1=f(y); k2=f([a+h*b/2 for a,b in zip(y,k1)]); k3=f([a+h*b/2 for a,b in zip(y,k2)]); k4=f([a+h*b for a,b in zip(y,k3)])
    return [a+h*(b+2*c+2*d+e)/6 for a,b,c,d,e in zip(y,k1,k2,k3,k4)]

def integrate(d):
    model=d.get('model'); p=d.get('parameters'); initial=d.get('initial'); span=d.get('t_span')
    if not isinstance(p,dict) or not isinstance(initial,list) or not isinstance(span,list) or len(span)!=2: raise ValueError('parameters, initial and t_span required')
    n=2 if model=='oscillator' else 1
    if len(initial)!=n: raise ValueError('wrong state dimension')
    y=[num(x,'initial') for x in initial]; original=y[:]; t,end=map(lambda v:num(v,'time'),span)
    start=t
    if end<=t: raise ValueError('positive time span required')
    label(d.get('time_unit')); units=d.get('state_units')
    if not isinstance(units,list) or len(units)!=n: raise ValueError('state_units dimension mismatch')
    for u in units: label(u)
    rtol=positive(d.get('rtol'),'rtol'); atol=positive(d.get('atol'),'atol')
    if not 1e-12<=rtol<=.1: raise ValueError('rtol outside [1e-12,0.1]')
    max_steps=integer(d.get('max_steps',20000),1,100000,'max_steps')
    if model in ('decay','logistic','relaxation'):
        rate=num(p.get('rate'),'rate')
        if rate<0: raise ValueError('negative rate unsupported')
    if model=='decay':
        f=lambda z:[-rate*z[0]]; exact=lambda dt:[original[0]*math.exp(-rate*dt)]
    elif model=='logistic':
        cap=positive(p.get('capacity'),'capacity')
        if y[0]<=0: raise ValueError('positive logistic initial required')
        f=lambda z:[rate*z[0]*(1-z[0]/cap)]; exact=lambda dt:[cap/(1+(cap/original[0]-1)*math.exp(-rate*dt))]
    elif model=='oscillator':
        omega=positive(p.get('omega'),'omega')
        f=lambda z:[z[1],-omega*omega*z[0]]
        exact=lambda dt:[original[0]*math.cos(omega*dt)+original[1]/omega*math.sin(omega*dt),original[1]*math.cos(omega*dt)-omega*original[0]*math.sin(omega*dt)]
    elif model=='relaxation':
        target=num(p.get('target'),'target'); exact=lambda dt:[target+(original[0]-target)*math.exp(-rate*dt)]
    else: raise ValueError('unsupported ODE model')
    h=positive(d.get('initial_step',(end-t)/20),'initial_step'); h=min(h,end-t)
    trajectory=[{'t':t,'y':y[:]}]; attempts=accepted=rejected=0; status='COMPLETE'; reason=None
    order=2 if model=='relaxation' else 5
    while t<end:
        if attempts>=max_steps: status='FAILED'; reason='step budget exhausted'; break
        h=min(h,end-t)
        if t+h==t: status='FAILED'; reason='time step below floating-point resolution'; break
        attempts+=1
        try:
            if model=='relaxation':
                step=lambda state,hh:[target+(state[0]-target)/(1+rate*hh)]
                coarse=step(y,h); fine=step(step(y,h/2),h/2); divisor=1
            else: coarse=rk4(y,h,f); fine=rk4(rk4(y,h/2,f),h/2,f); divisor=15
            for value in coarse+fine: num(value,'computed state')
            err=max(abs(a-b)/divisor/(atol+rtol*max(abs(old),abs(a))) for old,a,b in zip(y,fine,coarse))
            num(err,'local error')
        except (ValueError,OverflowError,ZeroDivisionError): status='FAILED'; reason='non-finite numerical stage'; break
        if err<=1:
            t=end if h==end-t else t+h; y=fine; accepted+=1; trajectory.append({'t':t,'y':y[:]})
        else: rejected+=1
        factor=5 if err==0 else min(5,max(.1,.9*err**(-1/order)))
        h*=factor
    errors=[max(abs(a-b) for a,b in zip(row['y'],exact(row['t']-start))) for row in trajectory]
    result={'schema':1,'operation':'integrate','model':model,'method':'implicit Euler step doubling' if model=='relaxation' else 'RK4 step doubling','status':status,'reason':reason,'attempts':attempts,'accepted_steps':accepted,'rejected_steps':rejected,'max_observed_analytic_absolute_error':max(errors),'trajectory':trajectory,'time_unit':d['time_unit'],'state_units':units,'local_error_is_global_bound':False}
    if model=='oscillator':
        e0=original[1]**2+omega**2*original[0]**2
        result['relative_energy_drift']=max(abs(row['y'][1]**2+omega**2*row['y'][0]**2-e0) for row in trajectory)/e0 if e0 else 0
    return result

def grid(spec):
    if not isinstance(spec,list) or len(spec)!=3: raise ValueError('grid must be [lo,hi,count]')
    lo=num(spec[0],'grid low'); hi=num(spec[1],'grid high'); n=integer(spec[2],3,501,'grid count')
    if not 0<=lo<hi: raise ValueError('grid needs 0<=lo<hi')
    return [lo+(hi-lo)*i/(n-1) for i in range(n)]
def profile(d):
    model=d.get('model')
    if model not in ('decay','product-decay'): raise ValueError('unsupported profile model')
    amp=num(d.get('amplitude'),'amplitude'); sigma=positive(d.get('sigma'),'sigma')
    if amp==0: raise ValueError('zero amplitude cannot identify decay')
    label(d.get('time_unit')); label(d.get('observation_unit'))
    obs=d.get('observations')
    if not isinstance(obs,list) or not 2<=len(obs)<=10000: raise ValueError('need 2..10000 observations')
    points=[]
    for row in obs:
        if not isinstance(row,dict): raise ValueError('observation must be object')
        t=num(row.get('t'),'observation time'); y=num(row.get('y'),'observation')
        if t<0: raise ValueError('negative observation time')
        points.append((t,y))
    aa=grid(d.get('a_grid')); bb=grid(d.get('b_grid')) if model=='product-decay' else [1.0]
    if len(aa)*len(bb)*len(points)>2000000: raise ValueError('grid budget exceeds 2,000,000 predictions')
    rows=[]; best=None
    for a in aa:
        scores=[]
        for b in bb:
            score=num(math.fsum(((amp*math.exp(-a*b*t)-y)/sigma)**2 for t,y in points),'likelihood score')
            scores.append((score,b))
            if best is None or score<best[0]: best=(score,a,b)
        score,b=min(scores); rows.append({'a':a,'profile_chi_square':score,'best_grid_b':b})
    support=[r['a'] for r in rows if r['profile_chi_square']-best[0]<=3.841459]
    boundary=best[1] in (aa[0],aa[-1]) or (model=='product-decay' and best[2] in (bb[0],bb[-1]))
    return {'schema':1,'operation':'profile','status':'GRID_RESULT','model':model,'noise_contract':'independent Gaussian, supplied known sigma','sigma':sigma,'minimum_chi_square':best[0],'best_grid_a':best[1],'best_grid_b':best[2] if model=='product-decay' else None,'best_identifiable_rate':best[1]*best[2],'minimum_on_boundary':boundary,'structural_identifiability':'only a*b, not individual factors' if model=='product-decay' else ('no decay information at all-zero times' if all(t==0 for t,y in points) else 'a under the declared model'),'profile':rows,'approximate_95_percent_support_a_values':support,'support_hull':[min(support),max(support)],'grid_resolution_a':aa[1]-aa[0],'limitation':'Finite-grid likelihood under a declared noise model; not arbitrary calibration or model validation.'}
def run(d):
    if not isinstance(d,dict) or type(d.get('schema')) is not int or d.get('schema')!=1: raise ValueError('schema must be 1')
    if d.get('operation')=='integrate': result=integrate(d)
    elif d.get('operation')=='profile': result=profile(d)
    else: raise ValueError('unsupported operation')
    result['input_contract']=d
    return result
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input'); ap.add_argument('--out',required=True); a=ap.parse_args()
    try:
        raw=Path(a.input).read_bytes()
        if len(raw)>2*1024*1024: raise ValueError('input exceeds 2 MiB')
        r=run(json.loads(raw)); r['input_sha256']=hashlib.sha256(raw).hexdigest(); r['solver_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        with Path(a.out).open('x',encoding='utf-8') as f: json.dump(r,f,indent=2,allow_nan=False)
    except (OSError,ValueError,TypeError,OverflowError,ZeroDivisionError) as e: ap.exit(2,'ERROR: '+str(e)+'\n')
if __name__=='__main__': main()
