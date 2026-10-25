"""Explicit combined private configuration/key-coverage probe; no HTTP binding."""
import argparse
import json
import os
from backend.ses_feedback_service import prepare


def check(environ=None,*,enabled=False,now=None):
    if enabled is not True:return {'status':'DISABLED'}
    try:
        prepared=prepare(environ,now=now)
        return {'status':'DISABLED'} if prepared is None else prepared.check(now=now)
    except Exception:return {'status':'CONFIGURATION_REJECTED'}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Check protected SES receiver configuration without starting HTTP')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(argv)
    result=check(dict(os.environ),enabled=args.check)
    print(json.dumps(result,sort_keys=True))
    return int(result['status']=='CONFIGURATION_REJECTED')


if __name__=='__main__':raise SystemExit(main())
