"""Probe official publisher Figure 1 assets without distributing or modifying them."""
import urllib.request
import json
import io
from PIL import Image

DOI="10.1371/journal.pcbi.1012818"
urls=[
 "https://journals.plos.org/ploscompbiol/article/figure/image?size=large&id="+DOI+".g001",
 "https://journals.plos.org/ploscompbiol/article/figure/image?size=original&id="+DOI+".g001",
 "https://journals.plos.org/ploscompbiol/article/asset?id="+DOI+".g001.PNG",
 "https://journals.plos.org/ploscompbiol/article/file?id="+DOI+".g001&type=figure",
]
rows=[]
for url in urls:
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
  with urllib.request.urlopen(req,timeout=20) as r:
   data=r.read(8000000)
   status=r.status
   typ=r.headers.get("Content-Type")
   final=r.url
  try:
   with Image.open(io.BytesIO(data)) as im:
    fmt=im.format
    dimensions=im.size
    im.verify()
  except Exception:
   fmt=None
   dimensions=None
  import hashlib
  rows.append({"url":url,"response_type":typ,"status":status,"final_url":final,
               "format":fmt,"dimensions":dimensions,"bytes":len(data),
               "sha256":hashlib.sha256(data).hexdigest() if fmt else None})
 except Exception as e:
  rows.append({"url":url,"error":str(e)[:200]})
print("PLOS_OFFICIAL_FIGURE_PROBE="+json.dumps(rows))
