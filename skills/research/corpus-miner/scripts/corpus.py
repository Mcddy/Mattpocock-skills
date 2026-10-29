"""Local content-addressed corpus, sparse retrieval, copy candidates and reversible entity decisions."""
import argparse, collections, hashlib, json, math, re, sqlite3, sys, unicodedata
from pathlib import Path

def load(path):
    if Path(path).stat().st_size>20000000: raise ValueError('JSON input exceeds 20 MB core limit')
    def pairs(xs):
        d={}
        for k,v in xs:
            if k in d: raise ValueError('duplicate JSON key '+k)
            d[k]=v
        return d
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON token')))
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()
def tokens(s): return re.findall(r'\w+',unicodedata.normalize('NFKC',s).casefold(),re.UNICODE)
def connect(path):
    db=sqlite3.connect(path); db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''CREATE TABLE IF NOT EXISTS versions(source_id TEXT,revision INTEGER,raw TEXT NOT NULL,record_hash TEXT NOT NULL,content_hash TEXT NOT NULL,active INTEGER NOT NULL,PRIMARY KEY(source_id,revision));
    CREATE UNIQUE INDEX IF NOT EXISTS one_active ON versions(source_id) WHERE active=1;
    CREATE TABLE IF NOT EXISTS decisions(sequence INTEGER PRIMARY KEY,decision_id TEXT UNIQUE NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);''')
    if db.execute("SELECT value FROM meta WHERE key='schema'").fetchone() not in (None,('1',)): raise ValueError('unsupported database schema')
    db.execute("INSERT OR IGNORE INTO meta VALUES('schema','1')"); db.commit(); return db
def validate(doc):
    if not isinstance(doc,dict) or not isinstance(doc.get('id'),str) or not doc['id'] or not isinstance(doc.get('text'),str): raise ValueError('each document needs nonempty id and literal text')
    if len(doc['text'])>2000000: raise ValueError('document exceeds 2 MB character ceiling')
    entities=doc.get('entities',[])
    if not isinstance(entities,list): raise ValueError('entities must be a list')
    for e in entities:
        if not isinstance(e,dict) or not isinstance(e.get('id'),str) or not e['id'] or not isinstance(e.get('name'),str) or not e['name']: raise ValueError('entity needs id/name strings')
        if 'attributes' in e and not isinstance(e['attributes'],dict): raise ValueError('entity attributes must be an object')
    canonical(doc)
def ingest(db,docs):
    if not isinstance(docs,list) or len(docs)>10000: raise ValueError('input must be at most 10000 documents')
    for doc in docs: validate(doc)
    if sum(len(canonical(doc)) for doc in docs)>8000000: raise ValueError('batch canonical text exceeds 8 million characters')
    if len(set(d['id'] for d in docs))!=len(docs): raise ValueError('duplicate source id within batch')
    report=[]
    with db:
        for doc in docs:
            raw=canonical(doc); rh=sha(raw); ch=sha(doc['text']); old=db.execute('SELECT revision,record_hash FROM versions WHERE source_id=? AND active=1',(doc['id'],)).fetchone()
            if old and old[1]==rh: report.append({'id':doc['id'],'status':'unchanged','revision':old[0]}); continue
            maximum=db.execute('SELECT max(revision) FROM versions WHERE source_id=?',(doc['id'],)).fetchone()[0] or 0
            db.execute('UPDATE versions SET active=0 WHERE source_id=?',(doc['id'],))
            db.execute('INSERT INTO versions VALUES(?,?,?,?,?,1)',(doc['id'],maximum+1,raw,rh,ch))
            report.append({'id':doc['id'],'status':'revised' if old else 'added','revision':maximum+1,'record_sha256':rh,'content_sha256':ch})
        count,size=db.execute('SELECT count(*),coalesce(sum(length(raw)),0) FROM versions WHERE active=1').fetchone()
        if count>10000 or size>20000000: raise ValueError('resulting active corpus exceeds core limit; batch rolled back, partition explicitly')
    return report
def active(db):
    count,size=db.execute('SELECT count(*),coalesce(sum(length(raw)),0) FROM versions WHERE active=1').fetchone()
    if count>10000 or size>20000000: raise ValueError('active corpus exceeds 10000 records or 20 million canonical characters; partition explicitly')
    return [(sid,rev,json.loads(raw),rh,ch) for sid,rev,raw,rh,ch in db.execute('SELECT source_id,revision,raw,record_hash,content_hash FROM versions WHERE active=1 ORDER BY source_id')]
def search(db,query,limit):
    docs=active(db); counts=[collections.Counter(tokens(d[2]['text'])) for d in docs]; q=collections.Counter(tokens(query)); n=len(docs)
    df=collections.Counter(k for c in counts for k in c); results=[]
    idf={k:math.log((1+n)/(1+df[k]))+1 for k in q}
    for d,c in zip(docs,counts):
        score=math.fsum((1+math.log(c[k]))*idf[k]*count for k,count in q.items() if c[k])
        if score:
            raw=d[2]['text']; match=next((m for m in re.finditer(r'\w+',raw,re.UNICODE) if tokens(m.group())[0] in q),None)
            offset=match.start() if match else 0
            results.append({'id':d[0],'revision':d[1],'score':score,'content_sha256':d[4],'span_start':offset,'span_end':min(len(raw),offset+200),'snippet':raw[offset:offset+200],'source_metadata':{k:v for k,v in d[2].items() if k not in ('text','entities')},'note':'Lexical score is relevance, not truth or independent corroboration.'})
    return sorted(results,key=lambda r:(-r['score'],r['id']))[:limit]
def families(db,threshold):
    docs=active(db)
    if len(docs)>2000: raise ValueError('near-copy comparison limited to 2000 active documents; partition a larger corpus explicitly')
    exact=collections.defaultdict(list)
    for sid,rev,d,rh,ch in docs: exact[ch].append({'id':sid,'revision':rev})
    shingles=[]
    for d in docs:
        ts=tokens(d[2]['text']); shingles.append(set(tuple(ts[i:i+3]) for i in range(max(0,len(ts)-2))))
    if (len(docs)-1)*sum(len(s) for s in shingles)>20000000: raise ValueError('near-copy shingle comparison-work exceeds 20 million; partition explicitly')
    near=[]
    for i in range(len(docs)):
        for j in range(i+1,len(docs)):
            if docs[i][4]==docs[j][4] or min(len(shingles[i]),len(shingles[j]))<4: continue
            score=len(shingles[i]&shingles[j])/len(shingles[i]|shingles[j])
            if score>=threshold: near.append({'a':docs[i][0],'b':docs[j][0],'jaccard_3shingle':score,'status':'CANDIDATE_NOT_MERGED'})
    return {'exact_content_families':[{'content_sha256':h,'members':m,'independence':'copies are one content family; provenance may still differ'} for h,m in sorted(exact.items()) if len(m)>1],'near_copy_candidates':near,'threshold':threshold}
def entities(db):
    found=collections.defaultdict(list)
    for sid,rev,d,rh,ch in active(db):
        for e in d.get('entities',[]): found[e['id']].append({'source_id':sid,'revision':rev,'name':e['name'],'attributes':e.get('attributes',{})})
    return found
def entity_candidates(db):
    es=entities(db); keys=sorted(es); result=[]
    if len(keys)>2000: raise ValueError('candidate entity scan limited to 2000 identities')
    comparison_work=0
    for i,a in enumerate(keys):
        namesa={tuple(tokens(o['name'])) for o in es[a]}
        for b in keys[i+1:]:
            namesb={tuple(tokens(o['name'])) for o in es[b]}
            if namesa&namesb:
                comparison_work+=len(es[a])*len(es[b])
                if comparison_work>2000000: raise ValueError('entity observation comparison-work exceeds 2 million; partition candidates explicitly')
                conflicts=[]
                for oa in es[a]:
                    for ob in es[b]:
                        for k in set(oa['attributes'])&set(ob['attributes']):
                            if oa['attributes'][k]!=ob['attributes'][k]: conflicts.append(k)
                result.append({'a':a,'b':b,'evidence':'normalised-name equality only','conflicting_attribute_keys':sorted(set(conflicts)),'status':'UNRESOLVED','observations':{a:es[a],b:es[b]}})
    return result
def resolved(db):
    es=entities(db); parent={k:k for k in es}; events=[(did,kind,json.loads(p)) for did,kind,p in db.execute('SELECT decision_id,kind,payload FROM decisions ORDER BY sequence')]
    undone={e[2]['undo'] for e in events if e[1]=='undo'}
    current=dict(db.execute('SELECT source_id,revision FROM versions WHERE active=1'))
    def root(k):
        while parent[k]!=k: k=parent[k]
        return k
    stale=[]
    for did,kind,p in events:
        if kind!='merge' or did in undone: continue
        if p['a'] not in parent or p['b'] not in parent: stale.append(did); continue
        if any(current.get(sid)!=rev for sid,rev in p.get('source_revisions',{}).items()): stale.append(did); continue
        a,b=root(p['a']),root(p['b']); parent[max(a,b)]=min(a,b)
    groups=collections.defaultdict(list)
    for k in parent: groups[root(k)].append(k)
    return {'groups':dict(groups),'stale_decisions_not_applied':stale,'note':'Only explicit reviewed merge events change identity; updates invalidate decisions tied to old source revisions.'}
def decision(db,p):
    if not isinstance(p,dict) or not isinstance(p.get('id'),str) or not p['id'] or not isinstance(p.get('reason'),str) or not p['reason'].strip(): raise ValueError('decision id and substantive reason required')
    if 'undo' in p:
        original=db.execute('SELECT kind FROM decisions WHERE decision_id=?',(p['undo'],)).fetchone()
        if original!=('merge',): raise ValueError('undo must name an existing merge decision')
        if any(json.loads(raw).get('undo')==p['undo'] for raw, in db.execute("SELECT payload FROM decisions WHERE kind='undo'")): raise ValueError('merge already undone')
        kind='undo'
    else:
        es=entities(db)
        if p.get('a') not in es or p.get('b') not in es or p['a']==p['b']: raise ValueError('merge requires two current distinct entity ids')
        kind='merge'; p=dict(p,source_revisions={o['source_id']:o['revision'] for k in (p['a'],p['b']) for o in es[k]})
    with db: db.execute('INSERT INTO decisions(decision_id,kind,payload) VALUES(?,?,?)',(p['id'],kind,canonical(p)))
    return resolved(db)
def export(db):
    count,size=db.execute('SELECT count(*),coalesce(sum(length(raw)),0) FROM versions').fetchone()
    if count>20000 or size>20000000 or db.execute('SELECT count(*) FROM decisions').fetchone()[0]>10000: raise ValueError('history export exceeds bounded snapshot scope; use an explicitly reviewed partition/export adapter')
    return {'schema_version':1,'versions':[dict(zip(('source_id','revision','raw','record_hash','content_hash','active'),r)) for r in db.execute('SELECT * FROM versions ORDER BY source_id,revision')],
            'decisions':[dict(zip(('sequence','decision_id','kind','payload'),r)) for r in db.execute('SELECT * FROM decisions ORDER BY sequence')]}
def restore(db,state):
    if not isinstance(state,dict) or state.get('schema_version')!=1 or not isinstance(state.get('versions'),list) or not isinstance(state.get('decisions'),list): raise ValueError('invalid export schema')
    if len(state['versions'])>20000 or len(state['decisions'])>10000: raise ValueError('import exceeds bounded version/log count')
    if sum(len(r.get('raw','')) for r in state['versions'] if isinstance(r,dict))>20000000: raise ValueError('import raw text exceeds 20 million characters')
    if db.execute('SELECT count(*) FROM versions').fetchone()[0] or db.execute('SELECT count(*) FROM decisions').fetchone()[0]: raise ValueError('import requires empty database')
    with db:
        for r in state['versions']:
            d=json.loads(r['raw']); validate(d)
            if d['id']!=r['source_id'] or sha(r['raw'])!=r['record_hash'] or sha(d['text'])!=r['content_hash'] or type(r['revision'])!=int or r['revision']<1 or r['active'] not in (0,1): raise ValueError('version integrity mismatch')
            db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?)',tuple(r[k] for k in ('source_id','revision','raw','record_hash','content_hash','active')))
        eventids=set(); undone=set(); previous_sequence=0
        for r in state['decisions']:
            p=json.loads(r['payload'])
            if r['kind'] not in ('merge','undo') or p.get('id')!=r['decision_id'] or not isinstance(p.get('reason'),str) or not p['reason'].strip(): raise ValueError('invalid decision record')
            if type(r['sequence'])!=int or r['sequence']<=previous_sequence: raise ValueError('decision sequence must increase')
            previous_sequence=r['sequence']
            if r['kind']=='merge':
                if not isinstance(p.get('a'),str) or not isinstance(p.get('b'),str) or p['a']==p['b'] or not isinstance(p.get('source_revisions'),dict): raise ValueError('invalid merge event')
                if not p['a'] or not p['b'] or not p['source_revisions']: raise ValueError('merge requires nonempty source commitments and identities')
                if any(not isinstance(sid,str) or type(rev)!=int or rev<1 for sid,rev in p['source_revisions'].items()): raise ValueError('invalid source revision commitment')
                represented=set()
                for sid,rev in p['source_revisions'].items():
                    source=db.execute('SELECT raw FROM versions WHERE source_id=? AND revision=?',(sid,rev)).fetchone()
                    if source is None: raise ValueError('merge commitment references absent source revision')
                    cited={e['id'] for e in json.loads(source[0]).get('entities',[])} & {p['a'],p['b']}
                    if not cited: raise ValueError('merge commitment does not cite either merged identity')
                    represented.update(cited)
                if represented!={p['a'],p['b']}: raise ValueError('merge commitments must represent both merged identities')
                eventids.add(p['id'])
            else:
                if p.get('undo') not in eventids or p['undo'] in undone: raise ValueError('undo must reference one earlier non-undone merge')
                undone.add(p['undo'])
            db.execute('INSERT INTO decisions VALUES(?,?,?,?)',tuple(r[k] for k in ('sequence','decision_id','kind','payload')))
    return {'status':'restored','versions':len(state['versions']),'decisions':len(state['decisions'])}
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('database'); sub=p.add_subparsers(dest='command',required=True)
    for cmd in ('ingest','decide','import'):
        s=sub.add_parser(cmd); s.add_argument('input')
    s=sub.add_parser('search'); s.add_argument('query'); s.add_argument('--limit',type=int,default=20)
    s=sub.add_parser('families'); s.add_argument('--threshold',type=float,default=.8)
    for cmd in ('entities','resolved','export'): sub.add_parser(cmd)
    a=p.parse_args()
    try:
        if not 0<=getattr(a,'threshold',.8)<=1 or not 1<=getattr(a,'limit',20)<=1000: raise ValueError('threshold 0..1 and limit 1..1000 required')
        db=connect(a.database)
        try:
            if a.command=='ingest': result=ingest(db,load(a.input))
            elif a.command=='search': result=search(db,a.query,a.limit)
            elif a.command=='families': result=families(db,a.threshold)
            elif a.command=='entities': result=entity_candidates(db)
            elif a.command=='resolved': result=resolved(db)
            elif a.command=='decide': result=decision(db,load(a.input))
            elif a.command=='import': result=restore(db,load(a.input))
            else: result=export(db)
            print(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2))
        finally: db.close()
    except (ValueError,TypeError,KeyError,OverflowError,OSError,sqlite3.Error) as e: print('ERROR: '+str(e),file=sys.stderr); return 2
    return 0
if __name__=='__main__': sys.exit(main())
