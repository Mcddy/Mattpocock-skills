"""Availability-aware rolling-origin univariate baselines and prequential residual intervals."""
import argparse, datetime, hashlib, json, math, statistics, sys
from pathlib import Path

def load(path):
    if Path(path).stat().st_size>12000000: raise ValueError('input exceeds 12 MB core limit')
    def pairs(xs):
        d={}
        for k,v in xs:
            if k in d: raise ValueError('duplicate JSON key '+k)
            d[k]=v
        return d
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON token')))
def stamp(s):
    if not isinstance(s,str): raise ValueError('timestamp must be text')
    if len(s)==10:
        return datetime.datetime.combine(datetime.date.fromisoformat(s),datetime.time(23,59,59,999999),datetime.timezone.utc)
    dt=datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
    if dt.tzinfo is None: raise ValueError('timestamps require timezone; date-only means UTC end of day')
    return dt.astimezone(datetime.timezone.utc)
def num(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)): raise ValueError('finite numeric value required')
    try: v=float(v)
    except OverflowError: raise ValueError('number outside supported finite range')
    if not math.isfinite(v): raise ValueError('non-finite number')
    return v
def forecasts(rows,origin,horizon,method,period,step):
    visible=[(i,r) for i,r in enumerate(rows) if r['t']<=origin and r['a']<=origin and r['value'] is not None]
    if not visible: raise ValueError('no observed value available at forecast origin')
    last_i,last=visible[-1]; known={r['t']:r['value'] for _,r in visible}; out=[]
    for h in range(1,horizon+1):
        target=origin+h*step; fallback=None; value=last['value']
        if method=='seasonal':
            prior=target-period*step
            while prior>origin: prior-=period*step
            if prior in known: value=known[prior]
            else: fallback='matching seasonal observation unavailable; latest-observation fallback'
        elif method=='drift':
            first=visible[0][1]; elapsed=(last['t']-first['t'])/step
            value=last['value'] if elapsed==0 else last['value']+(last['value']-first['value'])/elapsed*((target-last['t'])/step)
        if not math.isfinite(value): raise ValueError('forecast overflow')
        out.append({'horizon':h,'target':target.isoformat(),'prediction':value,'fallback':fallback,'origin':origin.isoformat(),'method':method})
    return out
def summary(results,scale):
    scored=[r for r in results if r.get('actual') is not None]
    if not scored: return {'n':0,'mae':None,'rmse':None,'mase':None,'bias':None,'interval_n':0,'coverage':None}
    errors=[r['prediction']-r['actual'] for r in scored]; mae=statistics.fmean(abs(e) for e in errors)
    intervals=[r for r in scored if r.get('interval') is not None]
    return {'n':len(scored),'mae':mae,'rmse':math.sqrt(statistics.fmean(e*e for e in errors)),
            'mase':mae/scale if scale is not None and scale>1e-12 else None,'mase_denominator':scale,
            'mase_suppressed_reason':'unavailable or tiny seasonal-difference denominator' if scale is None or scale<=1e-12 else None,
            'bias':statistics.fmean(errors),'interval_n':len(intervals),'coverage':statistics.fmean(r['interval'][0]<=r['actual']<=r['interval'][1] for r in intervals) if intervals else None,
            'percentage_errors':'not used; zeros and small denominators retained'}
def analyse(data):
    if not isinstance(data,dict) or data.get('schema_version')!=1: raise ValueError('schema_version 1 required')
    raw=data.get('observations'); origins=data.get('origins'); horizon=data.get('horizon',1); period=data.get('period',1); seconds=data.get('step_seconds',86400)
    if not isinstance(raw,list) or not 2<=len(raw)<=100000: raise ValueError('2..100000 observations required')
    if not isinstance(origins,list) or not origins or len(origins)>10000: raise ValueError('explicit origin list required')
    if len(raw)*len(origins)*3>5000000: raise ValueError('origin scan-work exceeds 5 million row visits; reduce scope or use a reviewed vectorised adapter')
    for name,v,maximum in [('horizon',horizon,1000),('period',period,10000),('step_seconds',seconds,31536000)]:
        if type(v)!=int or not 1<=v<=maximum: raise ValueError(name+' out of range')
    step=datetime.timedelta(seconds=seconds); rows=[]
    for r in raw:
        if not isinstance(r,dict): raise ValueError('observation must be object')
        t=stamp(r.get('timestamp')); available=stamp(r.get('available_at',r['timestamp']))
        if available<t: raise ValueError('available_at precedes observation timestamp; use an explicit forecast covariate outside this core')
        rows.append({'t':t,'a':available,'value':None if r.get('value') is None else num(r['value'])})
    if any(b['t']-a['t']!=step for a,b in zip(rows,rows[1:])): raise ValueError('timestamps must be strictly increasing on the declared regular grid; represent missing values with null')
    origins=[stamp(o) for o in origins]
    if len(set(origins))!=len(origins): raise ValueError('duplicate origin')
    origins.sort()
    grid={r['t'] for r in rows}
    if any(o not in grid for o in origins): raise ValueError('origins must align to observed grid positions')
    if len(origins)*horizon>100000: raise ValueError('forecast budget exceeded')
    if 3*(len(origins)*horizon)**2>5000000: raise ValueError('calibration scan-work exceeds 5 million comparisons')
    asof=stamp(data.get('evaluation_as_of',max(r['a'] for r in rows).isoformat()))
    alpha=num(data.get('alpha',.1)); minimum=data.get('minimum_calibration',5)
    if not 0<alpha<1 or type(minimum)!=int or not 2<=minimum<=10000: raise ValueError('alpha in (0,1), minimum_calibration 2..10000')
    values={r['t']:r for r in rows}; methods=['naive','seasonal','drift']; allresults={m:[] for m in methods}; violations=[]
    for cov in data.get('auxiliary',[]):
        if not isinstance(cov,dict): raise ValueError('auxiliary record must be object')
        origin=stamp(cov.get('origin')); availability=stamp(cov.get('available_at'))
        if availability>origin: violations.append({'feature':cov.get('feature'),'origin':origin.isoformat(),'available_at':availability.isoformat(),'status':'LOOKAHEAD_REJECTED'})
    split=data.get('candidate_split')
    if split:
        if not isinstance(split,dict): raise ValueError('candidate_split must be object')
        if stamp(split['training_includes_through'])>stamp(split['origin']): violations.append({'status':'TRAINING_AFTER_ORIGIN_REJECTED','candidate':split})
    scale_values=[r for r in rows if r['t']<=origins[0] and r['a']<=origins[0]]; scale_known={r['t']:r['value'] for r in scale_values if r['value'] is not None}
    diffs=[abs(v-scale_known[t-period*step]) for t,v in scale_known.items() if t-period*step in scale_known]; scale=statistics.fmean(diffs) if diffs else None
    for origin in origins:
        for m in methods:
            fs=forecasts(rows,origin,horizon,m,period,step)
            for f in fs:
                target=stamp(f['target']); obs=values.get(target)
                # Calibration uses only errors whose actual labels had arrived by this origin.
                prior=[abs(p['prediction']-p['actual']) for p in allresults[m] if p.get('actual') is not None and p['horizon']==f['horizon'] and stamp(p['actual_available_at'])<=origin]
                f['calibration_n']=len(prior); f['interval']=None
                if len(prior)>=minimum:
                    prior.sort(); rank=math.ceil((len(prior)+1)*(1-alpha))
                    if rank<=len(prior):
                        width=prior[rank-1]; f['interval']=[f['prediction']-width,f['prediction']+width]
                    else: f['interval_reason']='finite calibration cannot supply requested quantile; no finite interval claimed'
                else: f['interval_reason']='insufficient prior completed same-horizon errors'
                f['actual']=obs['value'] if obs and obs['a']<=asof else None
                f['actual_available_at']=obs['a'].isoformat() if obs else None
                if obs and obs['a']>asof: f['score_status']='CENSORED_NOT_YET_AVAILABLE'
                elif obs and obs['value'] is None: f['score_status']='MISSING_TARGET'
                elif not obs: f['score_status']='UNOBSERVED_FUTURE'
                else: f['score_status']='SCORED'
                allresults[m].append(f)
    metrics={m:summary(fs,scale) for m,fs in allresults.items()}
    selected=min(methods,key=lambda m:(metrics[m]['mae'] is None,metrics[m]['mae'] if metrics[m]['mae'] is not None else math.inf,methods.index(m))) if any(v['n'] for v in metrics.values()) else None
    final=[]; final_origin=data.get('final_origin')
    if final_origin:
        fo=stamp(final_origin)
        if fo not in grid or fo<origins[-1]: raise ValueError('final origin must be on grid and not precede backtest origins')
        # No selection using labels not available at deployment origin.
        for m,fs in allresults.items():
            deployment_scores=[dict(f,actual=f['actual'] if f.get('actual_available_at') and stamp(f['actual_available_at'])<=fo else None) for f in fs]
            metrics[m]['deployment_selection_mae']=summary(deployment_scores,scale)['mae']
        allowed=[m for m in methods if metrics[m]['deployment_selection_mae'] is not None]
        selected=min(allowed,key=lambda m:(metrics[m]['deployment_selection_mae'],methods.index(m))) if allowed else 'naive'
        final=forecasts(rows,fo,horizon,selected,period,step)
        for f in final: f.update(actual=None,score_status='UNMEASURED_FINAL_FORECAST')
    shifts=[]; observed=[r for r in rows if r['value'] is not None and r['a']<=asof]
    if len(observed)>=12:
        # Exploratory retrospective window contrast only, not a significance test.
        for i in range(6,len(observed)-5):
            before=statistics.median(r['value'] for r in observed[i-6:i]); after=statistics.median(r['value'] for r in observed[i:i+6])
            shifts.append({'timestamp':observed[i]['t'].isoformat(),'median_shift':after-before})
        shifts=sorted(shifts,key=lambda s:-abs(s['median_shift']))[:5]
    return {'schema_version':1,'metrics':metrics,'backtests':allresults,'selected_method':selected,'final_forecasts':final,'availability_violations':violations,'retrospective_shift_candidates':shifts,
            'limitations':['univariate regular-grid baselines, no causal attribution','intervals use prior same-horizon absolute residuals; dependent/shifted series have no guaranteed nominal coverage','deployment selection uses completed labels only; final horizon unscored','null is missing; zero is observed','retrospective shift candidates are not validated changepoints']}
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('input'); p.add_argument('--out'); a=p.parse_args()
    try:
        result=analyse(load(a.input)); result['input_sha256']=hashlib.sha256(Path(a.input).read_bytes()).hexdigest(); text=json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)
        if a.out:
            with open(a.out,'x',encoding='utf-8',newline='\n') as f: f.write(text+'\n')
        else: print(text)
    except (ValueError,TypeError,KeyError,OverflowError,OSError) as e: print('ERROR: '+str(e),file=sys.stderr); return 2
    return 0
if __name__=='__main__': sys.exit(main())
