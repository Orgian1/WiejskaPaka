"""Explicit read-only connection probe. Default invocation performs no file/DB work."""
import argparse
import json
import os
from backend.ses_feedback_database import load_config


def check(environ=None,*,connect=False):
    if connect is not True:return {'status':'DISABLED'}
    con=None
    try:
        target=load_config(environ)
        if target is None:return {'status':'DISABLED'}
        con=target()
        return {'status':'DATABASE_VALID'}
    except Exception:return {'status':'DATABASE_REJECTED'}
    finally:
        if con is not None:
            try:con.connection.close()
            except Exception:pass


def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only protected SES test-database probe')
    parser.add_argument('--connect',action='store_true')
    args=parser.parse_args(argv)
    result=check(dict(os.environ),connect=args.connect)
    print(json.dumps(result,sort_keys=True))
    return int(result['status']=='DATABASE_REJECTED')


if __name__=='__main__':raise SystemExit(main())
