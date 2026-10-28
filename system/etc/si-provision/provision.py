#!/usr/bin/env python3
"""Explicit provisioning. Ordinary chezmoi/chezetc apply never invokes this tool."""
import argparse, shutil, grp, hashlib, json, os, pathlib, pwd, subprocess, tempfile, urllib.request
from storage import check_mounts, CONFIG
HERE = pathlib.Path(__file__).resolve().parent

def run(*args):
    subprocess.run(args, check=True)

def get(db, key):
    try: return db(key)
    except KeyError: return None

def account_plan():
    # Complete collision checks before changing anything. Never rename/renumber.
    for name, uid, gid, home, shell in [('m',1000,1000,'/home/m','/bin/fish'),('media',954,950,'/home/media','/bin/false')]:
        u=get(pwd.getpwnam,name); byid=get(pwd.getpwuid,uid)
        g=get(grp.getgrnam,name); bygid=get(grp.getgrgid,gid)
        if (u and (u.pw_uid,u.pw_gid,u.pw_dir)!=(uid,gid,home)) or (byid and byid.pw_name!=name):
            raise RuntimeError('User identity collision: '+name)
        if (g and g.gr_gid!=gid) or (bygid and bygid.gr_name!=name):
            raise RuntimeError('Group identity collision: '+name)
        yield name,uid,gid,home,shell,bool(u),bool(g)

def accounts(apply):
    plan=list(account_plan())
    for name,uid,gid,home,shell,exists,gexists in plan:
        print(name, 'preserve existing account' if exists else 'create account')
        if apply:
            if not gexists:run('groupadd','--gid',str(gid),name)
            if not exists:run('useradd','--uid',str(uid),'--gid',str(gid),'--home-dir',home,'--shell',shell,'--create-home',name)
    if apply:
        run('usermod','-aG','media','m')
        if get(grp.getgrnam,'docker'):run('usermod','-aG','docker','m')
        if get(pwd.getpwnam,'plex'):run('usermod','-aG','media','plex')

def directories(apply):
    check_mounts(json.loads(CONFIG.read_text()))
    entries=json.loads((HERE/'directories.json').read_text())
    for target, attrs in entries.items():
        p=pathlib.Path(target)
        if not target.startswith(('/mnt/storage/','/appData/')):raise RuntimeError('Unexpected directory')
        if p.exists() or p.is_symlink():
            if not p.is_dir():raise RuntimeError('Not a directory: '+target)
            print('Preserve', target)
            continue
        print('Create',target)
        if apply:
            p.mkdir(parents=True,mode=int(attrs['mode'],8))
            os.chmod(p,int(attrs['mode'],8));os.chown(p,attrs['uid'],attrs['gid'])
    for target,source in [('/home/m/downloads','/mnt/storage/meta/downloads'),('/var/lib/plexmediaserver','/mnt/storage/meta/opt/plexmediaserver')]:
        p=pathlib.Path(target)
        if p.is_symlink() and p.resolve()==pathlib.Path(source):continue
        if p.exists() or p.is_symlink():raise RuntimeError('Refusing to replace existing path: '+target)
        print('Link',target,'->',source)
        if apply:p.symlink_to(source)

def mergerfs(apply):
    pin=json.loads((HERE/'mergerfs.json').read_text())
    existing=subprocess.run(['rpm','-q','mergerfs'],capture_output=True,text=True)
    if existing.returncode==0:
        print('Preserving installed mergerfs:',existing.stdout.strip(), '(no implicit upgrade)')
        return
    version=subprocess.check_output(['rpm','-E','%fedora'],text=True).strip()
    arch=subprocess.check_output(['uname','-m'],text=True).strip()
    if version!=pin['fedora'] or arch!=pin['arch']:raise RuntimeError('Pinned mergerfs package does not match this OS/architecture')
    print('Install',pin['url'])
    if apply:
        with tempfile.TemporaryDirectory() as d:
            rpm=pathlib.Path(d)/'mergerfs.rpm'
            urllib.request.urlretrieve(pin['url'],rpm)
            if hashlib.sha256(rpm.read_bytes()).hexdigest()!=pin['sha256']:raise RuntimeError('mergerfs checksum mismatch')
            # Upstream artifact pinned by publisher SHA256; no repository signature assumed.
            run('dnf','install','-y','--nogpgcheck',str(rpm))

def beets(apply):
    check_mounts(json.loads(CONFIG.read_text()))
    source=pathlib.Path('/home/m/dockers/beets-customizations')
    target=pathlib.Path('/mnt/storage/meta/appData/beets')
    if not source.is_dir() or not target.is_dir():raise RuntimeError('Provision/restore Beets directories first')
    for tree in ['plugins','genres']:
        for src in (source/tree).rglob('*'):
            if src.is_symlink():raise RuntimeError('Unexpected source symlink')
            if not src.is_file():continue
            dst=target/src.relative_to(source)
            if dst.exists() or dst.is_symlink():
                print('Preserve',dst)
                continue
            print('Seed',dst)
            if apply:
                dst.parent.mkdir(parents=True,exist_ok=True)
                # Exclusive create: even a concurrent existing file is never overwritten.
                with src.open('rb') as inp, dst.open('xb') as out:shutil.copyfileobj(inp,out)
                os.chmod(dst,0o644);os.chown(dst,1000,950)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['accounts','directories','mergerfs','beets'])
    p.add_argument('--apply',action='store_true',help='without this flag only print/check')
    args=p.parse_args()
    if args.apply and os.geteuid()!=0:raise RuntimeError('Root required for --apply')
    globals()[args.action](args.apply)
if __name__=='__main__':main()
