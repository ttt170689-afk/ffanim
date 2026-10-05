#!/usr/bin/env python3
import os, re, json, uuid, shutil
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

ROOT=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(ROOT,'uploads_server'); os.makedirs(DATA, exist_ok=True)
MAX=500*1024*1024
class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/upload': self.send_error(404); return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>MAX+5*1024*1024: self.send_error(413,'Archive is larger than 500 MB'); return
            ctype=self.headers.get('Content-Type','')
            boundary=ctype.split('boundary=',1)[1].encode() if 'boundary=' in ctype else b''
            if not boundary: self.send_error(400,'multipart file is required'); return
            body=self.rfile.read(length)
            marker=b'--'+boundary
            chunks=body.split(marker)
            payload=None
            for chunk in chunks:
                if b'filename=' in chunk:
                    head, payload = chunk.split(b'\r\n\r\n',1); payload=payload.rstrip(b'\r\n-'); break
            if payload is None: self.send_error(400,'file is required'); return
            token=uuid.uuid4().hex[:12]
            path=os.path.join(DATA,token+'.zip')
            with open(path,'wb') as out: out.write(payload)
            size=os.path.getsize(path)
            if size>MAX: os.remove(path); self.send_error(413,'Archive is larger than 500 MB'); return
            self.send_json({'token':token,'size':size,'url':'/?share='+token})
        except Exception as e: self.send_error(500,str(e))
    def do_GET(self):
        m=re.fullmatch(r'/api/share/([a-f0-9]{12})',urlparse(self.path).path)
        if m:
            path=os.path.join(DATA,m.group(1)+'.zip')
            if not os.path.isfile(path): self.send_error(404,'Share not found'); return
            self.send_response(200); self.send_header('Content-Type','application/zip'); self.send_header('Content-Length',str(os.path.getsize(path))); self.end_headers()
            with open(path,'rb') as f: shutil.copyfileobj(f,self.wfile,1024*1024)
            return
        super().do_GET()
    def send_json(self,obj):
        data=json.dumps(obj).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)

PORT=int(os.environ.get('PORT','8000'))
print(f'ZIP Viewer server: http://0.0.0.0:{PORT}')
ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
