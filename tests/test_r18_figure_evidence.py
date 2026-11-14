"""Small, redistribution-safe regression tests for SharePack R18.

No commercial paper images, no local absolute paths, no internet access.
"""
import copy
import hashlib
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

import fitz
from pypdf import PdfReader
from PIL import Image, ImageDraw

from sharepack.figure_evidence import (PLAN_VERSION, digest, extract_reviewed,
    verify_reviewed, FigureEvidenceError)


class FigureSourceFixtureTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.dir=Path(self.temp.name)
        im=Image.new('RGB',(600,320),'white');d=ImageDraw.Draw(im)
        d.rectangle((20,30,300,270),fill='#457ca5');d.rectangle((330,30,580,270),fill='#99bbcc')
        b=BytesIO();im.save(b,format='PNG')
        self.pdf=self.dir/'synthetic.pdf'
        doc=fitz.open();p=doc.new_page()
        x=p.insert_image(fitz.Rect(60,70,460,285),stream=b.getvalue())
        q=doc.new_page();q.insert_text((60,100),'Fig. 1 | Simulated evidence image',fontsize=14)
        doc.save(self.pdf);doc.close()
        reader=PdfReader(self.pdf);source=next(i.data for i in reader.pages[0].images if i.indirect_reference.idnum==x);reader.close()
        self.plan={'contract':PLAN_VERSION,'paper_pdf_sha256':digest(self.pdf),
            'review_decision':'FIGURE_PLAN_APPROVED_FOR_PRIVATE_REVIEW',
            'figures':[{'id':'Fig1','figure_number':1,'image_pdf_page':1,'caption_pdf_page':2,
                        'caption_phrase':'Fig. 1 |','method':'original_pdf_xobject','approved_xref':x,
                        'expected_image_sha256':hashlib.sha256(source).hexdigest()}]}
        self.plan_path=self.dir/'plan.json';self.save()

    def tearDown(self):self.temp.cleanup()
    def save(self):self.plan_path.write_text(json.dumps(self.plan),encoding='utf-8')

    def test_cross_page_caption_and_original_image(self):
        out=self.dir/'out';r=extract_reviewed(self.pdf,self.plan_path,out)
        self.assertEqual(len(r['figures']),1)
        self.assertEqual(r['figures'][0]['caption_pdf_page'],2)
        self.assertEqual(verify_reviewed(self.pdf,out/'figure_manifest.json',self.plan_path)['status'],'PASS_SOURCE_BYTES_ONLY')
        a=json.loads((out/'assets.json').read_text())
        self.assertEqual(a['assets'][0]['review_status'],'PENDING')

    def test_wrong_caption_page_rejected(self):
        self.plan['figures'][0]['caption_pdf_page']=1;self.save()
        with self.assertRaisesRegex(FigureEvidenceError,'CAPTION_FIGURE_NUMBER_MISMATCH'):
            extract_reviewed(self.pdf,self.plan_path,self.dir/'out')

    def test_wrong_xref_rejected(self):
        self.plan['figures'][0]['approved_xref']=10000;self.save()
        with self.assertRaisesRegex(FigureEvidenceError,'XREF_NOT_DRAWN_ON_FIGURE_PAGE'):
            extract_reviewed(self.pdf,self.plan_path,self.dir/'out')

    def test_tamper_and_recompute_manifest_hash_still_rejected(self):
        out=self.dir/'out';r=extract_reviewed(self.pdf,self.plan_path,out)
        asset=out/r['figures'][0]['filename'];asset.write_bytes(b'bad')
        m=out/'figure_manifest.json';d=json.loads(m.read_text());d['figures'][0]['sha256']=digest(asset);m.write_text(json.dumps(d))
        with self.assertRaisesRegex(FigureEvidenceError,'INVALID_IMAGE'):
            verify_reviewed(self.pdf,m,self.plan_path)

    def test_unreviewed_plan_never_accepted(self):
        self.plan['review_decision']='UNREVIEWED';self.save()
        with self.assertRaisesRegex(FigureEvidenceError,'EXPLICIT_PLAN_REVIEW_REQUIRED'):
            extract_reviewed(self.pdf,self.plan_path,self.dir/'out')

if __name__=='__main__':unittest.main()
