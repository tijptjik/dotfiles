#!/usr/bin/python3
"""Reject executable payloads in Sonarr and Radarr torrents; never executes downloaded files."""
import base64,datetime,fcntl,json,os,pathlib,subprocess,sys,urllib.request,urllib.error,xml.etree.ElementTree as ET
BAD={'.exe','.scr','.lnk','.msi','.msp','.bat','.cmd','.ps1','.vbs','.vbe','.js','.jse','.wsf','.wsh','.com','.cpl','.hta'}
STATE=pathlib.Path('/var/lib/si-media-guard')
ROOT=pathlib.Path('/mnt/storage/meta/downloads')
def suspicious(name):
 normalized=name.replace('\\','/').rstrip(' .').casefold()
 return pathlib.PurePosixPath(normalized).suffix in BAD
def reject(torrent,row,reasons,rpc,sonarr,save,redownload=True):
 # Preserve downloaded bytes. Sonarr removeFromClient=true would delete them.
 rpc('torrent-stop',{'ids':[torrent['id']]})
 sonarr('queue/'+str(row['id'])+'?removeFromClient=false&blocklist=true&skipRedownload='+str(not redownload).lower(),method='DELETE')
 save({'hash':torrent['hashString'],'name':torrent['name'],'reasons':reasons,'blocked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'replacement_requested':redownload,'data_preserved':True})
 rpc('torrent-remove',{'ids':[torrent['id']],'delete-local-data':False})
def main():
 os.umask(0o077);STATE.mkdir(parents=True,exist_ok=True)
 lock=(STATE/'lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 dry='--dry-run' in sys.argv
 obj=json.loads(subprocess.check_output(['docker','inspect','transmission']))[0]
 env=dict(x.split('=',1) for x in obj['Config']['Env'] if '=' in x)
 auth=base64.b64encode((env['USER']+':'+env['PASS']).encode()).decode()
 sid=''
 def rpc(method,args):
  nonlocal sid
  for _ in range(2):
   req=urllib.request.Request('http://127.0.0.1:9091/transmission/rpc',data=json.dumps({'method':method,'arguments':args}).encode(),headers={'Authorization':'Basic '+auth,'X-Transmission-Session-Id':sid})
   try:
    with urllib.request.urlopen(req,timeout=20) as r:d=json.load(r)
    if d['result']!='success':raise RuntimeError('Transmission RPC failed')
    return d['arguments']
   except urllib.error.HTTPError as e:
    if e.code==409:sid=e.headers['X-Transmission-Session-Id'];continue
    raise
  raise RuntimeError('Transmission session negotiation failed')
 def app_api(app,port):
  key=ET.parse('/mnt/storage/meta/appData/'+app+'/config.xml').findtext('ApiKey')
  def request(path,method='GET'):
   req=urllib.request.Request('http://127.0.0.1:'+str(port)+'/api/v3/'+path,method=method,headers={'X-Api-Key':key})
   with urllib.request.urlopen(req,timeout=30) as r:
    raw=r.read();return json.loads(raw) if raw else None
  return request
 byhash={};errors=[]
 for app,port in [('sonarr',8989),('radarr',7878)]:
  try:
   request=app_api(app,port);queue=[];page=1
   while True:
    data=request('queue?pageSize=1000&page='+str(page))
    queue+=data['records']
    if len(queue)>=data['totalRecords'] or not data['records']:break
    page+=1
   for row in queue:
    if row.get('downloadId'):
     h=row['downloadId'].lower()
     if h in byhash and byhash[h][0]!=app:raise RuntimeError('Torrent claimed by multiple applications')
     byhash[h]=(app,row,request)
  except Exception as exc:errors.append(app+': '+type(exc).__name__)
 torrents=rpc('torrent-get',{'fields':['id','hashString','name','downloadDir','metadataPercentComplete','files','percentDone']})['torrents']
 checked={'sonarr':0,'radarr':0};bad=0
 for t in torrents:
  h=t['hashString'].lower()
  if h not in byhash or t.get('metadataPercentComplete',0)<1:continue
  app,row,request=byhash[h]
  checked[app]+=1
  receipt=STATE/(h+'.json')
  if receipt.exists():
   if not dry:
    rpc('torrent-stop',{'ids':[t['id']]})
    rpc('torrent-remove',{'ids':[t['id']],'delete-local-data':False})
   continue
  reasons=[f['name'] for f in t['files'] if suspicious(f['name'])]
  # Detect a PE executable disguised with a media suffix once that file is complete.
  for f in t['files']:
   if f.get('bytesCompleted',0)<f.get('length',1):continue
   d=t['downloadDir']
   if d.startswith('/data/meta/downloads'):d=str(ROOT)+d[len('/data/meta/downloads'):]
   elif d.startswith('/downloads'):d=str(ROOT)+d[len('/downloads'):]
   p=(pathlib.Path(d)/f['name']).resolve()
   if not p.is_relative_to(ROOT.resolve()) or not p.is_file():continue
   with p.open('rb') as stream:
    if stream.read(2)==b'MZ':reasons.append(f['name']+' [Windows executable header]')
  if not reasons:continue
  bad+=1
  if dry:print(json.dumps({'would_reject':t['name'],'reasons':reasons}));continue
  recent=0
  for p in STATE.glob('*.json'):
   try:
    r=json.loads(p.read_text())
    if r.get('replacement_requested') and (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(r['blocked_at'])).total_seconds()<3600:recent+=1
   except (ValueError,KeyError):pass
  def save(r):
   r['application']=app
   tmp=receipt.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2));tmp.replace(receipt)
  reject(t,row,sorted(set(reasons)),rpc,request,save,recent<3)
  print('Rejected unsafe '+app+' torrent:',t['name'],flush=True)
 print(json.dumps({'checked_torrents':checked,'unsafe':bad,'dry_run':dry}))
 if errors:raise RuntimeError('Some catalogs could not be checked: '+', '.join(errors))
if __name__=='__main__':main()
