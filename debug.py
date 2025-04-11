from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json

def api_request(url, api_key, post=False):
    req = Request(url, headers={'Authorization': f'Bearer {api_key}'})
    if post:
        req.method = 'POST'
    try:
        with urlopen(req, timeout=20) as response:
            code = response.getcode()
            resp_data = response.read()
            json_data = json.loads(resp_data.decode('utf-8'))
            return code, json_data
    except HTTPError as e:
        code = e.getcode()
        try:
            error_resp = e.read()
            error_json = json.loads(error_resp.decode('utf-8'))
        except Exception:
            error_json = None
        print("HTTPError: API request failed with code", code)
        return (code, error_json)
    except URLError as e:
        print("URLError: API request failed:", e)
        return None, None

api_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI0NjQ5MDdlZi1jZGQzLTQ4ZGYtODI2Zi01ZTc3MzY4MTZlN2EiLCJ1c2VybmFtZSI6ImpiaHVsIiwiaWF0IjoxNzM2NTU1NTM4fQ.TdNSY3fdwRTFnWtq1YeDfVibKm3NP2-bRyC2YdsduSU'

resp_code, res= api_request('http://192.168.1.235:13378/ping', api_key)
print(resp_code)
print(res)

resp_code, res= api_request('http://192.168.1.235:13378/api/authorize', api_key, True)
print(resp_code)
print(res)