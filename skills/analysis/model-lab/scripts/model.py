"""Train-only preprocessing, development selection, and a sealed single-audit test lifecycle."""
import argparse, datetime, hashlib, json, math, os, statistics, sys
from pathlib import Path

def load(path):
    def pairs(xs):
        d={}
        for k,v in xs:
            if k in d: raise ValueError('duplicate JSON key '+k)
            d[k]=v
        return d
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON token')))
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, value):
    with open(path,'x',encoding='utf-8',newline='\n') as f: json.dump(value,f,ensure_ascii=False,allow_nan=False,indent=2); f.write('\n')
def num(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)): raise ValueError('expected finite numeric value')
    try: v=float(v)
    except OverflowError: raise ValueError('number outside supported finite range')
    if not math.isfinite(v): raise ValueError('non-finite numeric value')
    return v
def stamp(v):
    if not isinstance(v,str): raise ValueError('time must be ISO text')
    dt=datetime.datetime.fromisoformat(v.replace('Z','+00:00'))
    if dt.tzinfo is None: raise ValueError('time must include timezone')
    return dt.astimezone(datetime.timezone.utc)
def ids(rows,field):
    result=set()
    for r in rows:
        v=r.get(field)
        if not isinstance(v,str) or not v: raise ValueError('nonempty string '+field+' required')
        if v in result and field=='id': raise ValueError('duplicate row id')
        result.add(v)
    return result
def contract_check(c):
    if not isinstance(c,dict) or c.get('schema_version')!=1: raise ValueError('contract schema_version 1 required')
    if c.get('task') not in ('regression','binary'): raise ValueError('task must be regression or binary')
    fs=c.get('features'); target=c.get('target')
    if not isinstance(fs,list) or not fs or any(not isinstance(x,str) or not x for x in fs) or len(set(fs))!=len(fs): raise ValueError('unique feature names required')
    reserved={target,'id',c.get('group_field'),c.get('time_field')}
    if any(x in reserved for x in fs): raise ValueError('features include target, identifiers or split metadata')
    if not isinstance(target,str) or not target: raise ValueError('target name required')
    availability=c.get('feature_availability')
    if not isinstance(availability,dict) or any(availability.get(f)!='known_at_prediction' for f in fs):
        raise ValueError('every feature needs explicit known_at_prediction declaration; declarations need independent evidence')
    if c.get('split') not in ('group','time','group_time'): raise ValueError('split must explicitly be group, time or group_time')
    if c['split'] in ('group','group_time') and not isinstance(c.get('group_field'),str): raise ValueError('group_field required')
    if c['split'] in ('time','group_time') and not isinstance(c.get('time_field'),str): raise ValueError('time_field required')
    return c
def rows_check(rows,c,labelled=True):
    if not isinstance(rows,list) or not rows or len(rows)>100000: raise ValueError('rows must contain 1..100000 objects')
    if any(not isinstance(r,dict) for r in rows): raise ValueError('row must be object')
    ids(rows,'id')
    for r in rows:
        missing=set(c['features'])-set(r)
        if missing: raise ValueError('missing feature keys: '+','.join(sorted(missing)))
        for f in c['features']:
            if r[f] is not None: num(r[f])
        if labelled:
            y=num(r.get(c['target']))
            if c['task']=='binary' and y not in (0.,1.): raise ValueError('binary targets must be 0 or 1')
    return rows
def boundary(a,b,c):
    if ids(a,'id')&ids(b,'id'): raise ValueError('row id overlap across split')
    if c['split'] in ('group','group_time') and ids(a,c['group_field'])&ids(b,c['group_field']): raise ValueError('entity group overlap across split')
    if c['split'] in ('time','group_time'):
        field=c['time_field']
        if max(stamp(r.get(field)) for r in a)>=min(stamp(r.get(field)) for r in b): raise ValueError('time boundary is not strictly chronological')
def preprocess(rows,c):
    state={}
    for f in c['features']:
        values=[num(r[f]) for r in rows if r[f] is not None]
        if not values: raise ValueError('training feature entirely missing: '+f)
        median=statistics.median(values); filled=[median if r[f] is None else num(r[f]) for r in rows]
        mean=statistics.fmean(filled); scale=math.sqrt(statistics.fmean((v-mean)**2 for v in filled))
        state[f]={'median':median,'mean':mean,'scale':scale or 1.}
    return state
def design(rows,c,state):
    return [[1.]+[(state[f]['median'] if r[f] is None else num(r[f]))/state[f]['scale']-state[f]['mean']/state[f]['scale'] for f in c['features']] for r in rows]
def solve(a,b):
    a=[list(row)+[v] for row,v in zip(a,b)]; n=len(b)
    for k in range(n):
        pivot=max(range(k,n),key=lambda i:abs(a[i][k]))
        if abs(a[pivot][k])<1e-12: raise ValueError('singular model; increase ridge or remove redundant features')
        a[k],a[pivot]=a[pivot],a[k]; v=a[k][k]; a[k]=[x/v for x in a[k]]
        for i in range(n):
            if i!=k:
                v=a[i][k]; a[i]=[x-v*y for x,y in zip(a[i],a[k])]
    return [row[-1] for row in a]
def sigmoid(x): return 1/(1+math.exp(-max(-40.,min(40.,x))))
def fit_weights(x,y,task,penalty):
    p=len(x[0]); n=len(x)
    if task=='regression':
        a=[[math.fsum(row[j]*row[k] for row in x)/n+(penalty if j==k and j else 0) for k in range(p)] for j in range(p)]
        b=[math.fsum(row[j]*v for row,v in zip(x,y))/n for j in range(p)]
        return solve(a,b)
    # Convex logistic objective; fixed conservative steps. Convergence is reported, not assumed.
    w=[0.]*p; step=.5/(p+penalty); converged=False
    for iteration in range(3000):
        errs=[sigmoid(math.fsum(v*z for v,z in zip(row,w)))-target for row,target in zip(x,y)]
        grad=[math.fsum(e*row[j] for row,e in zip(x,errs))/n+(penalty*w[j] if j else 0) for j in range(p)]
        if max(abs(g) for g in grad)<1e-6: converged=True; break
        w=[v-step*g for v,g in zip(w,grad)]
    return w,{'iterations':iteration+1,'gradient_max':max(abs(g) for g in grad),'converged':converged}
def predictions(model,rows):
    if not isinstance(model,dict) or model.get('schema_version')!=1: raise ValueError('invalid model schema')
    c=contract_check(model['contract']); rows_check(rows,c,False)
    if model['kind']=='mean':
        constant=num(model['constant'])
        if c['task']=='binary' and not 0<=constant<=1: raise ValueError('binary baseline outside probability range')
        return [constant]*len(rows)
    if model['kind'] != ('logistic' if c['task']=='binary' else 'ridge'): raise ValueError('model kind does not match contract')
    weights=model.get('weights')
    if not isinstance(weights,list) or len(weights)!=len(c['features'])+1: raise ValueError('coefficient dimension mismatch')
    for w in weights: num(w)
    for f in c['features']:
        state=model['preprocessing'][f]
        for k in ('median','mean','scale'): num(state[k])
        if state['scale']<=0: raise ValueError('preprocessing scale must be positive')
    values=[math.fsum(a*b for a,b in zip(row,model['weights'])) for row in design(rows,c,model['preprocessing'])]
    return [sigmoid(v) for v in values] if c['task']=='binary' else values
def metric(y,p,task):
    if task=='binary':
        loss=-statistics.fmean(t*math.log(max(1e-15,min(1-1e-15,v)))+(1-t)*math.log(max(1e-15,min(1-1e-15,1-v))) for t,v in zip(y,p))
        return {'log_loss':loss,'brier':statistics.fmean((t-v)**2 for t,v in zip(y,p)), 'accuracy_at_fixed_0_5':statistics.fmean((v>=.5)==bool(t) for t,v in zip(y,p)), 'n':len(y)}
    return {'mse':statistics.fmean((t-v)**2 for t,v in zip(y,p)),'mae':statistics.fmean(abs(t-v) for t,v in zip(y,p)),'n':len(y)}
def train(c,trainrows,devrows,test_sha):
    contract_check(c); rows_check(trainrows,c); rows_check(devrows,c); boundary(trainrows,devrows,c)
    state=preprocess(trainrows,c); x=design(trainrows,c,state); y=[num(r[c['target']]) for r in trainrows]
    if len(c['features'])>64 or (len(trainrows)*len(c['features'])*3000>30000000 and c['task']=='binary') or (len(trainrows)*(len(c['features'])+1)**2>20000000 and c['task']=='regression'): raise ValueError('core resource ceiling exceeded; use an explicitly reviewed adapter')
    if c['task']=='binary' and len(set(y))<2: raise ValueError('binary training needs both classes')
    base={'schema_version':1,'contract':c,'kind':'mean','constant':statistics.fmean(y)}; models=[base]
    for penalty in (.01,1.,10.):
        result=fit_weights(x,y,c['task'],penalty); convergence=None
        if c['task']=='binary': result,convergence=result
        models.append({'schema_version':1,'contract':c,'kind':'logistic' if c['task']=='binary' else 'ridge','weights':result,'preprocessing':state,'penalty':penalty,'convergence':convergence})
    devy=[num(r[c['target']]) for r in devrows]; scores=[metric(devy,predictions(m,devrows),c['task']) for m in models]
    key='log_loss' if c['task']=='binary' else 'mse'; selected=min(range(len(models)),key=lambda i:scores[i][key]); model=models[selected]
    model.update(test_sha256=test_sha,selection={'criterion':key,'selected_index':selected,'candidate_scores':scores,'threshold':.5 if c['task']=='binary' else None},
                 split_manifest={'train_ids':sorted(ids(trainrows,'id')),'dev_ids':sorted(ids(devrows,'id')),
                                 'seen_groups':sorted(ids(trainrows+devrows,c['group_field'])) if c['split'] in ('group','group_time') else [],
                                 'latest_time':max(stamp(r[c['time_field']]) for r in trainrows+devrows).isoformat() if c['split'] in ('time','group_time') else None},
                 limitations=['numeric tabular features only','availability declarations are not semantic leakage detection','development selection can overfit; sealed test must not be used to retune','probabilities are not calibrated automatically'])
    return model
def audit(model,rows):
    c=contract_check(model['contract']); rows_check(rows,c)
    seen=set(model['split_manifest']['train_ids']+model['split_manifest']['dev_ids'])
    if ids(rows,'id')&seen: raise ValueError('test overlaps fitted or development rows')
    if c['split'] in ('group','group_time') and ids(rows,c['group_field'])&set(model['split_manifest']['seen_groups']): raise ValueError('test shares development/training groups')
    if c['split'] in ('time','group_time') and min(stamp(r[c['time_field']]) for r in rows)<=stamp(model['split_manifest']['latest_time']): raise ValueError('test time boundary violated')
    p=predictions(model,rows); y=[num(r[c['target']]) for r in rows]
    return {'schema_version':1,'status':'TEST_AUDITED_ONCE_WITHIN_THIS_LEDGER','metrics':metric(y,p,c['task']),'predictions':[{'id':r['id'],'prediction':v,'target':t} for r,v,t in zip(rows,p,y)],'limitations':model['limitations']}
def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    seal=sub.add_parser('seal-test'); seal.add_argument('test'); seal.add_argument('out')
    fit=sub.add_parser('fit'); fit.add_argument('contract'); fit.add_argument('train'); fit.add_argument('dev'); fit.add_argument('seal'); fit.add_argument('out')
    pred=sub.add_parser('predict'); pred.add_argument('model'); pred.add_argument('rows'); pred.add_argument('out')
    test=sub.add_parser('audit-test'); test.add_argument('model'); test.add_argument('test'); test.add_argument('seal'); test.add_argument('ledger')
    a=p.parse_args()
    try:
        if a.command=='seal-test': save(a.out,{'schema_version':1,'test_sha256':digest(a.test),'bytes':Path(a.test).stat().st_size,'note':'Byte commitment only; labels not parsed. Keep this fixed before model selection.'})
        elif a.command=='fit':
            sealdata=load(a.seal); commitment=sealdata.get('test_sha256')
            if not isinstance(commitment,str) or len(commitment)!=64: raise ValueError('invalid test commitment')
            if digest(a.train)==commitment or digest(a.dev)==commitment: raise ValueError('test file is being used in fit/select')
            result=train(load(a.contract),load(a.train),load(a.dev),commitment)
            result.update(train_sha256=digest(a.train),dev_sha256=digest(a.dev)); save(a.out,result)
        elif a.command=='predict': save(a.out,[{'id':r['id'],'prediction':v} for r,v in zip(load(a.rows),predictions(load(a.model),load(a.rows)))])
        else:
            model=load(a.model); sealdata=load(a.seal)
            if digest(a.test)!=sealdata.get('test_sha256') or model.get('test_sha256')!=sealdata.get('test_sha256'): raise ValueError('sealed test changed or different model commitment')
            # Ledger tied to the seal, not caller-selected output. Exclusive lock is retained even on failure.
            lock=Path(a.seal).with_name(Path(a.seal).name+'.audit-lock')
            with open(lock,'x',encoding='utf-8') as f: f.write(json.dumps({'model_sha256':digest(a.model),'test_sha256':digest(a.test)}))
            result=audit(model,load(a.test)); result.update(model_sha256=digest(a.model),test_sha256=digest(a.test)); save(a.ledger,result)
    except (ValueError,TypeError,KeyError,OverflowError,OSError) as e: print('ERROR: '+str(e),file=sys.stderr); return 2
    return 0
if __name__=='__main__': sys.exit(main())
