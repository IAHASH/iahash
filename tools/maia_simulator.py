"""Synthetic Maia-style producer using the real queue/API in process; never imports Maia."""
from pathlib import Path
import tempfile

import httpx
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from iahash_core import make_pair, key_id, verify_receipt
from iahash_client import Client
from iahash_server.app import create_app


def main():
    with tempfile.TemporaryDirectory(prefix='iahash-simulator-') as directory:
        path = Path(directory)
        sk = Ed25519PrivateKey.generate()
        trust = {('simulator.lab', 'LAB', key_id(sk.public_key())): sk.public_key()}
        token = 'synthetic-simulator-token-not-operational'
        app = create_app(db_path=path/'registry.sqlite', private_key=sk,
                         issuer_id='simulator.lab', environment='LAB', api_token=token)
        with TestClient(app) as server:
            def transport(request):
                response = server.request(request.method, request.url.path,
                                          content=request.content, headers=dict(request.headers))
                return httpx.Response(response.status_code, content=response.content,
                                      headers=response.headers, request=request)
            with Client(base_url='https://simulator.invalid', queue_path=path/'queue.sqlite',
                        api_token=token, trusted_keys=trust, expected_environment='LAB',
                        transport=httpx.MockTransport(transport)) as client:
                key = client.enqueue(make_pair('Synthetic prompt', 'Synthetic response'))
                result = client.send(key)
                assert result['status'] == 'CONFIRMED'
                check = verify_receipt(result['certificate'], trusted_keys=trust,
                                       expected_environment='LAB', originals={
                                           'par1': {'text': 'Synthetic prompt'},
                                           'par2': {'text': 'Synthetic response'}})
                assert check['status'] == 'VERIFIED_CONTENT'
        print('PASS: synthetic producer -> durable queue -> receipt -> offline originals verification')


if __name__ == '__main__':
    main()
