"""Validate an explicitly enabled private pin file without DB/network or writes.

CONFIGURATION_VALID is structural/pinned-key readiness, not verification that
an arbitrary certificate is issued by AWS or that a topic policy is correct.
"""
import json
import os
from backend.ses_feedback_config import load_config


def check(environ,*,now=None):
    try:
        config=load_config(environ,now=now)
        if config is None:return {'status':'DISABLED'}
        return {'status':'CONFIGURATION_VALID','pins':len(config.pins)}
    except Exception:return {'status':'CONFIGURATION_REJECTED'}


def main():
    result=check(dict(os.environ))
    print(json.dumps(result,sort_keys=True))
    return int(result['status']=='CONFIGURATION_REJECTED')


if __name__=='__main__':raise SystemExit(main())
