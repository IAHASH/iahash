"""Isolated CI container lifecycle check; no ports published, synthetic identity."""
import argparse
import os
import secrets
import subprocess
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    args = parser.parse_args()
    label = 'iahash-ci-' + uuid.uuid4().hex
    volume, container = label + '-data', label + '-server'
    environment = dict(os.environ, IAHASH_API_TOKEN=secrets.token_hex(32))

    def docker(*arguments, check=True):
        result = subprocess.run(['docker', *arguments], check=check,
                                capture_output=True, text=True, env=environment, timeout=60)
        if check and result.returncode:
            raise RuntimeError('Container operation failed')
        return result

    def start(database):
        docker('run', '-d', '--name', container, '--network', 'none',
               '-e', 'IAHASH_API_TOKEN', '-v', volume + ':/data', args.image,
               '--db', '/data/' + database, '--private', '/data/issuer.private',
               '--issuer-id', 'docker.lab', '--environment', 'LAB')

    def ready():
        for _ in range(30):
            result = docker('exec', container, 'python', '-c',
                            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/pair-v1/ready',timeout=2)", check=False)
            if result.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError('Container readiness failed')

    exercise = '''
import os, pathlib, urllib.request
from cryptography.hazmat.primitives import serialization
from iahash_core import make_pair, canonical_bytes, strict_json_loads, key_id, verify_receipt
pub=serialization.load_pem_public_key(pathlib.Path('/data/issuer.pub').read_bytes())
p=make_pair('Synthetic prompt','Synthetic response')
r=urllib.request.Request('http://127.0.0.1:8000/api/pair-v1/receipts',data=canonical_bytes(p),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['IAHASH_API_TOKEN'],'Idempotency-Key':'a'*64})
with urllib.request.urlopen(r,timeout=5) as response:
    saved=response.read()
cert=strict_json_loads(saved)
assert verify_receipt(cert,trusted_keys={('docker.lab','LAB',key_id(pub)):pub},expected_environment='LAB')['status']=='VERIFIED_RECEIPT'
marker=pathlib.Path('/data/expected.json')
if marker.exists(): assert marker.read_bytes()==saved
else: marker.write_bytes(saved)
print('PASS durable receipt')
'''
    docker('volume', 'create', volume)
    try:
        docker('run', '--rm', '--network', 'none', '-v', volume + ':/data',
               '--entrypoint', 'python', args.image, '-m', 'iahash_server',
               'init-key', '--private', '/data/issuer.private', '--public', '/data/issuer.pub')
        start('registry.sqlite')
        ready()
        docker('exec', container, 'python', '-c', exercise)
        docker('restart', container)
        ready()
        docker('exec', container, 'python', '-c', exercise)
        for command, source, output in [('backup', 'registry.sqlite', 'snapshot.sqlite'),
                                         ('restore', 'snapshot.sqlite', 'restored.sqlite')]:
            docker('exec', container, 'python', '-m', 'iahash_server', command,
                   '--source', '/data/' + source, '--output', '/data/' + output)
        docker('rm', '-f', container)
        start('restored.sqlite')
        ready()
        docker('exec', container, 'python', '-c', exercise)
        print('PASS: non-root image, persistent identity, restart, backup and isolated restore')
    finally:
        docker('rm', '-f', container, check=False)
        docker('volume', 'rm', volume, check=False)


if __name__ == '__main__':
    main()
