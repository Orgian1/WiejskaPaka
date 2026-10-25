"""Explicit local-test receiver launcher. Never run automatically at import.

Without --serve: no private files, DB, listener, AWS or SMTP work. A deployment
needs a separately reviewed service definition and HTTPS/proxy; none is installed.
"""
import argparse
import json
import os
from backend.ses_feedback_service import prepare


def execute(environ,*,serve=False,host='127.0.0.1',port=8011):
    if serve is not True:return {'status':'DISABLED'}
    try:
        if host not in ('127.0.0.1','::1') or type(port) is not int or not 1<=port<=65535:
            raise ValueError('Local test bind required')
        prepared=prepare(environ)
        if prepared is None:raise ValueError('Explicit complete service configuration required')
        app=prepared.build_app()
        import uvicorn
        uvicorn.run(app,host=host,port=port,reload=False,workers=1,access_log=False,
                    proxy_headers=False,limit_concurrency=32,backlog=32,
                    timeout_keep_alive=5,timeout_graceful_shutdown=5)
        return {'status':'STOPPED'}
    except (Exception,SystemExit):return {'status':'LAUNCHER_REJECTED'}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Explicit loopback-only SES test receiver')
    parser.add_argument('--serve',action='store_true')
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8011)
    args=parser.parse_args(argv)
    result=execute(dict(os.environ),serve=args.serve,host=args.host,port=args.port)
    print(json.dumps(result,sort_keys=True))
    return int(result['status']=='LAUNCHER_REJECTED')


if __name__=='__main__':raise SystemExit(main())
