"""Declared-DAG backdoor validation and discrete-stratum ATE. No network or code imports."""
import argparse, collections, datetime, hashlib, json, math, random, statistics, sys
from pathlib import Path

def number(v):
    if isinstance(v, bool) or not isinstance(v, (float, int)):
        raise ValueError('numeric values must be JSON numbers, not booleans')
    try: x = float(v)
    except OverflowError: raise ValueError('number outside supported finite range')
    if not math.isfinite(x): raise ValueError('non-finite numeric value')
    return x

def strict_load(path):
    if Path(path).stat().st_size>12000000: raise ValueError('input exceeds 12 MB core limit')
    def pairs(xs):
        d = {}
        for k,v in xs:
            if k in d: raise ValueError('duplicate JSON key: '+k)
            d[k] = v
        return d
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('non-finite JSON token')))

def graph_check(spec):
    nodes = spec.get('nodes'); edges = spec.get('edges'); z = spec.get('adjustment', [])
    if not isinstance(nodes, list) or not 1<=len(nodes)<=200 or any(not isinstance(n,str) or not n for n in nodes) or len(set(nodes)) != len(nodes):
        raise ValueError('nodes must be unique nonempty strings')
    if not isinstance(edges,list) or len(edges)>5000 or any(not isinstance(e,list) or len(e)!=2 or any(n not in nodes for n in e) for e in edges):
        raise ValueError('edges must name node pairs')
    if not isinstance(z,list) or len(z)>20 or len(set(z)) != len(z) or any(n not in nodes for n in z): raise ValueError('invalid adjustment nodes or control count exceeds 20')
    x,y = spec.get('treatment'),spec.get('outcome')
    if x not in nodes or y not in nodes or x == y: raise ValueError('distinct treatment/outcome nodes required')
    observed = spec.get('observed')
    if not isinstance(observed,list) or any(n not in nodes for n in observed) or x not in observed or y not in observed:
        raise ValueError('invalid observed-node declaration')
    children = {n:set() for n in nodes}; parents = {n:set() for n in nodes}
    for a,b in edges: children[a].add(b); parents[b].add(a)
    remaining = {n:len(parents[n]) for n in nodes}; q = [n for n in nodes if not remaining[n]]; count=0
    while q:
        n=q.pop(); count+=1
        for c in children[n]:
            remaining[c]-=1
            if not remaining[c]: q.append(c)
    if count != len(nodes): raise ValueError('graph must be acyclic')
    descendants=set(); q=list(children[x])
    while q:
        n=q.pop()
        if n not in descendants: descendants.add(n); q.extend(children[n])
    reasons=[]
    if x in z or y in z: reasons.append('treatment or outcome cannot be adjustment variables')
    if set(z)&descendants: reasons.append('adjustment includes a treatment descendant: '+','.join(sorted(set(z)&descendants)))
    if set(z)-set(observed): reasons.append('adjustment includes unobserved nodes')
    # Backdoor graph removes outgoing treatment edges. D-separation uses the moralised ancestral graph.
    bp={n:set(parents[n])-{x} for n in nodes}
    ancestor=set([x,y]+z); q=list(ancestor)
    while q:
        n=q.pop()
        for p in bp[n]:
            if p not in ancestor: ancestor.add(p); q.append(p)
    und={n:set() for n in ancestor}
    for n in ancestor:
        ps=bp[n]&ancestor
        for p in ps: und[n].add(p); und[p].add(n)
        for p in ps: und[p].update(ps-{p})
    reached=set(); q=[x]
    while q:
        n=q.pop()
        if n in reached or n in z: continue
        reached.add(n); q.extend(und[n]-reached-set(z))
    if y in reached: reasons.append('open backdoor path remains under the declared graph')
    return {'identified_under_declared_graph':not reasons,'reasons':reasons,
            'assumptions':['graph correctness including latent common causes','consistency','no interference','positivity in target strata']}

def stratify(rows, spec):
    z=spec.get('adjustment',[]); groups=collections.defaultdict(lambda: {0:[],1:[]})
    x,y=spec['treatment'],spec['outcome']
    if not isinstance(rows,list) or not 1<=len(rows)<=20000: raise ValueError('rows must contain 1..20000 entries')
    ids=set()
    for r in rows:
        if not isinstance(r,dict): raise ValueError('every row must be an object')
        if 'id' not in r or not isinstance(r['id'],str) or not r['id'] or r['id'] in ids: raise ValueError('unique string row ids required')
        ids.add(r['id'])
        t=r.get(x)
        if isinstance(t,bool) or t not in (0,1): raise ValueError('binary 0/1 treatment required')
        outcome=number(r.get(y)); key=[]
        for c in z:
            v=r.get(c)
            if v is None or isinstance(v,(dict,list,bool)) or not isinstance(v,(str,int,float)): raise ValueError('adjustment values must be explicit nonmissing categories')
            if isinstance(v,(int,float)): number(v)
            key.append(json.dumps(v,ensure_ascii=False,allow_nan=False))
        groups[tuple(key)][t].append(outcome)
    return groups

def estimate(groups):
    n=sum(len(v[0])+len(v[1]) for v in groups.values()); supported=[]; unsupported=[]; terms=[]
    for k,v in sorted(groups.items()):
        counts={str(t):len(v[t]) for t in (0,1)}
        entry={'stratum':[json.loads(x) for x in k],'counts':counts,'weight':(len(v[0])+len(v[1]))/n}
        if not all(v[t] for t in (0,1)):
            unsupported.append(entry); continue
        effect=statistics.fmean(v[1])-statistics.fmean(v[0]); entry['difference']=effect
        supported.append(entry); terms.append(entry['weight']*effect)
    return {'target_n':n,'supported_strata':supported,'unsupported_strata':unsupported,
            'standardised_difference':math.fsum(terms) if not unsupported else None}

def analyse(data):
    if not isinstance(data,dict) or data.get('schema_version') != 1: raise ValueError('schema_version 1 required')
    spec=data.get('graph')
    if not isinstance(spec,dict): raise ValueError('graph object required')
    identification=graph_check(spec); rows=data.get('rows'); groups=stratify(rows,spec)
    description=estimate(groups)
    result={'schema_version':1,'identification':identification,'descriptive_contrasts':description,
            'causal_estimate':None,'uncertainty':{'status':'not estimated'}}
    if not identification['identified_under_declared_graph']:
        result['status']='UNIDENTIFIED'; return result
    if description['unsupported_strata']:
        result['status']='SUPPORT_GAP'; return result
    result['status']='IDENTIFIED_UNDER_ASSUMPTIONS'; result['causal_estimate']=description['standardised_difference']
    bootstrap=data.get('bootstrap',{})
    if bootstrap:
        if not isinstance(bootstrap,dict): raise ValueError('bootstrap must be an object')
        field=bootstrap.get('cluster'); runs=bootstrap.get('runs',500); seed=bootstrap.get('seed',17)
        if isinstance(runs,bool) or not isinstance(runs,int) or not 100<=runs<=5000: raise ValueError('bootstrap runs must be 100..5000')
        if runs*len(rows)>2000000: raise ValueError('bootstrap row-work exceeds 2 million resampled rows; reduce runs or use a reviewed adapter')
        if isinstance(seed,bool) or not isinstance(seed,int): raise ValueError('seed must be integer')
        if not isinstance(field,str) or not field: raise ValueError('explicit cluster field required for bootstrap')
        clusters=collections.defaultdict(list)
        for r in rows:
            if field not in r or not isinstance(r[field],(str,int)) or isinstance(r[field],bool): raise ValueError('missing or invalid cluster id')
            clusters[r[field]].append(r)
        if len(clusters)<4:
            result['uncertainty']={'status':'NOT_ESTIMATED','reason':'fewer than four clusters; no reliable cluster-bootstrap interval claimed'}
        else:
            keys=list(clusters); rng=random.Random(seed); estimates=[]
            for _ in range(runs):
                sample=[]
                for j in range(len(keys)):
                    for r in clusters[rng.choice(keys)]: sample.append(dict(r,id=str(j)+':'+r['id']))
                value=estimate(stratify(sample,spec))['standardised_difference']
                if value is not None: estimates.append(value)
            if len(estimates)<.9*runs:
                result['uncertainty']={'status':'NOT_ESTIMATED','reason':'resampled support failures exceed 10%; conditional percentile interval suppressed','valid':len(estimates),'runs':runs}
            else:
                estimates.sort(); lo=estimates[int(.025*(len(estimates)-1))]; hi=estimates[int(.975*(len(estimates)-1))]
                result['uncertainty']={'status':'EXPLORATORY_CLUSTER_PERCENTILE','level':.95,'low':lo,'high':hi,'clusters':len(clusters),'valid':len(estimates),'runs':runs,'seed':seed,'limitations':'Not proof of assumptions or reliable small-cluster coverage.'}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('input'); p.add_argument('--out'); args=p.parse_args()
    try:
        result=analyse(strict_load(args.input)); raw=Path(args.input).read_bytes(); result['input_sha256']=hashlib.sha256(raw).hexdigest()
        text=json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)
        if args.out:
            with open(args.out,'x',encoding='utf-8',newline='\n') as f: f.write(text+'\n')
        else: print(text)
    except (ValueError,TypeError,KeyError,OverflowError,OSError) as e: print('ERROR: '+str(e),file=sys.stderr); return 2
    return 0
if __name__=='__main__': sys.exit(main())
