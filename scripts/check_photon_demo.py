"""One-shot Windows/Linux diagnosis using only the fixed public Wroclaw query.

Never prints addresses from responses, proxy values, credentials or tracebacks.
Keeps TLS verification enabled. Does not change application/environment settings.
"""
import argparse
import json
import os
from pathlib import Path
import ssl
import sys
import time
import urllib.error
import urllib.request
import httpx
from backend.photon_geocoder import PUBLIC_URL,normalize


def classified(response):
    result={'status':response.status_code}
    try:
        data=response.json()
        if isinstance(data,dict):
            diagnostic=json.dumps(data,ensure_ascii=True).lower()
            result['unsupported_language']=response.status_code==400 and 'language' in diagnostic and ('not supported' in diagnostic or 'unsupported' in diagnostic)
            if isinstance(data.get('features'),list):
                result['features_count']=len(data['features'])
                result['legacy_null_property_failure']=any(isinstance(f,dict) and isinstance(f.get('properties'),dict) and any(key in f['properties'] and f['properties'][key] is None for key in ['name','street','housenumber','postcode','city','state','country']) for f in data['features'])
        if response.status_code==200:
            try:normalize(data);result['normalization_ok']=True
            except (ValueError,TypeError):result['normalization_ok']=False
    except (ValueError,TypeError):
        if response.status_code==200:result['normalization_ok']=False
    return result


def failure(error):
    text=str(error).lower()
    if 'certificate' in text or 'ssl' in text:return {'error':'TLS_VERIFICATION_FAILED'}
    if '403' in text or isinstance(error,httpx.ProxyError):return {'error':'PROXY_OR_NETWORK_POLICY'}
    return {'error':'NETWORK_UNAVAILABLE'}


def diagnose(*,pause=time.sleep):
    minimal={'q':'Wroclaw','limit':1}
    legacy={'q':'Wroclaw','limit':5,'countrycode':'PL','lang':'pl'}
    fixed={**legacy,'lang':'default'}
    results={}
    try:
        request=urllib.request.Request(PUBLIC_URL+'?'+str(httpx.QueryParams(minimal)),headers={'Accept':'application/json'})
        with urllib.request.urlopen(request,timeout=8) as response:results['urllib_minimal']={'status':response.status}
    except (OSError,urllib.error.URLError) as error:results['urllib_minimal']=failure(error)
    for label,params,verify in [('httpx_minimal_default_trust',minimal,True),('httpx_legacy_language_system_trust',legacy,'system'),('httpx_fixed_system_trust',fixed,'system')]:
        pause(1.1)
        try:
            context=ssl.create_default_context() if verify=='system' else verify
            with httpx.Client(timeout=8,verify=context,trust_env=True,follow_redirects=False) as client:
                results[label]=classified(client.get(PUBLIC_URL,params=params,headers={'User-Agent':'WiejskaPaka-AddressSearch/1.0','Accept':'application/json'}))
        except (httpx.HTTPError,OSError) as error:results[label]=failure(error)
    if results['httpx_legacy_language_system_trust'].get('unsupported_language'):
        results['diagnosis']='CONFIRMED_UNSUPPORTED_LANG_PL'
    elif results['httpx_legacy_language_system_trust'].get('legacy_null_property_failure'):
        results['diagnosis']='CONFIRMED_NULL_OPTIONAL_ADDRESS_FIELDS'
    elif results['httpx_minimal_default_trust'].get('error')=='TLS_VERIFICATION_FAILED' and results['urllib_minimal'].get('status')==200:
        results['diagnosis']='CONFIRMED_TLS_TRUST_STORE_DIFFERENCE'
    elif results['httpx_fixed_system_trust'].get('status')==200 and results['httpx_fixed_system_trust'].get('normalization_ok'):results['diagnosis']='FIXED_PHOTON_QUERY_REACHABLE'
    else:results['diagnosis']='EXTERNAL_ACCESS_NOT_CONFIRMED'
    results['runtime']={'python':sys.version.split()[0],'httpx':httpx.__version__,'platform':sys.platform}
    results['bindings_present']={key:bool(os.environ.get(key)) for key in ['HTTPS_PROXY','https_proxy','SSL_CERT_FILE','SSL_CERT_DIR']}
    return results


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path)
    args=parser.parse_args(argv)
    if args.report and args.report.exists():parser.error('Raport już istnieje; wybierz nowy plik')
    data=diagnose();text=json.dumps(data,indent=2,ensure_ascii=True)+'\n'
    if args.report:args.report.write_text(text,encoding='utf-8')
    print(text,end='')
    return 0 if data['httpx_fixed_system_trust'].get('status')==200 and data['httpx_fixed_system_trust'].get('normalization_ok') else 1


if __name__=='__main__':raise SystemExit(main())
