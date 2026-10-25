"""Check archive-key file shape/permissions without DB, network or activation."""
import json
from backend.ses_review_keys import load_config


def check(environ=None):
    try:return {'status':'DISABLED' if load_config(environ) is None else 'KEYS_VALID'}
    except Exception:return {'status':'KEYS_REJECTED'}


def main():
    result=check()
    print(json.dumps(result,sort_keys=True))
    return int(result['status']=='KEYS_REJECTED')


if __name__=='__main__':raise SystemExit(main())
