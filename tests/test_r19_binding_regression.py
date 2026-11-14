"""Standalone negative tests for the source/plan/SharePack-assets trust boundary.

Runs entirely on an original synthetic PDF; no copyrighted figures required.
"""
import copy, hashlib, json, tempfile, unittest
from io import BytesIO
from pathlib import Path
import fitz
from pypdf import PdfReader
from PIL import Image
from sharepack.figure_evidence import PLAN_VERSION, digest, extract_reviewed, verify_reviewed, FigureEvidenceError


class BindingRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.d=Path(self.temp.name)
        self.pdf=self.d/'synthetic.pdf'
        doc=fitz.open();p=doc.new_page();self.xrefs=[];self.images=[]
        for k in (1,2):
            im=Image.new('RGB',(640,400), (70*k,80,120))
            raw=BytesIO();im.save(raw,format='PNG');self.images.append(raw.getvalue())
            self.xrefs.append(p.insert_image(fitz.Rect(40+280*(k-1),80,300+280*(k-1),275),stream=raw.getvalue()))
        doc.new_page().insert_text((60,90),'Fig. 1 | Two microscopy samples', fontsize=13)
        doc.save(self.pdf);doc.close()
        reader=PdfReader(self.pdf); images={i.indirect_reference.idnum:i.data for i in reader.pages[0].images}; self.raw=[images[x] for x in self.xrefs];reader.close()
        self.plan={'contract':PLAN_VERSION,'paper_pdf_sha256':digest(self.pdf),
                   'review_decision':'FIGURE_PLAN_APPROVED_FOR_PRIVATE_REVIEW','figures':[
                   {'id':'Fig1','figure_number':1,'image_pdf_page':1,'caption_pdf_page':2,
                    'caption_phrase':'Fig. 1 |','method':'original_pdf_xobject',
                    'approved_xref':self.xrefs[0],
                    'expected_image_sha256':hashlib.sha256(self.raw[0]).hexdigest()}]}
        self.plan_path=self.d/'plan.json';self.plan_path.write_text(json.dumps(self.plan))
        self.out=self.d/'result';extract_reviewed(self.pdf,self.plan_path,self.out)
        self.m=self.out/'figure_manifest.json';self.a=self.out/'assets.json'

    def tearDown(self): self.temp.cleanup()
    def loadm(self):return json.loads(self.m.read_text())
    def loada(self):return json.loads(self.a.read_text())
    def savem(self, d):self.m.write_text(json.dumps(d))
    def savea(self, d):self.a.write_text(json.dumps(d))
    def verify(self):return verify_reviewed(self.pdf,self.m,self.plan_path)

    def test_valid_baseline(self):
        r=self.verify();self.assertTrue(r['reviewed_plan_binding']);self.assertTrue(r['compatible_asset_binding'])
        self.assertFalse(r['science_verified'])

    def test_changing_pdf_panel_while_rehashing_manifest_is_rejected(self):
        m=self.loadm();rec=m['figures'][0];target=self.raw[1]
        (self.out/rec['filename']).write_bytes(target)
        rec['approved_xref']=self.xrefs[1]
        rec['sha256']=hashlib.sha256(target).hexdigest()
        rec['original_xobject_sha256']=rec['sha256']
        self.savem(m)
        with self.assertRaisesRegex(FigureEvidenceError,'PLAN_MANIFEST_BINDING_DRIFT:XREF'):self.verify()

    def test_manifest_label_rewrite_rejected(self):
        m=self.loadm();m['figures'][0]['figure_number']=2;self.savem(m)
        with self.assertRaisesRegex(FigureEvidenceError,'PLAN_MANIFEST_BINDING_DRIFT'):self.verify()

    def test_caption_placement_rewrite_rejected(self):
        m=self.loadm();m['figures'][0]['caption_pdf_page']=1;self.savem(m)
        with self.assertRaisesRegex(FigureEvidenceError,'PLAN_MANIFEST_BINDING_DRIFT'):self.verify()

    def test_missing_approved_plan_rejected(self):
        with self.assertRaisesRegex(FigureEvidenceError,'APPROVED_PLAN_REQUIRED'):
            verify_reviewed(self.pdf,self.m)

    def test_assets_wrong_figure_label_rejected(self):
        a=self.loada();a['assets'][0]['figure']='Figure 2';self.savea(a)
        with self.assertRaisesRegex(FigureEvidenceError,'ASSET_MANIFEST_BINDING_DRIFT'):self.verify()

    def test_assets_hash_rewrite_rejected(self):
        a=self.loada();a['assets'][0]['sha256']='0'*64;self.savea(a)
        with self.assertRaisesRegex(FigureEvidenceError,'ASSET_MANIFEST_BINDING_DRIFT'):self.verify()

    def test_assets_caption_page_rewrite_rejected(self):
        a=self.loada();a['assets'][0]['caption_pdf_page']=1;self.savea(a)
        with self.assertRaisesRegex(FigureEvidenceError,'ASSET_MANIFEST_BINDING_DRIFT'):self.verify()

    def test_assets_missing_rejected(self):
        self.a.unlink()
        with self.assertRaisesRegex(FigureEvidenceError,'COMPATIBLE_ASSET_MANIFEST_REQUIRED'):self.verify()

    def test_review_status_cannot_prove_science(self):
        a=self.loada();a['assets'][0]['review_status']='VISUAL_REVIEWED';self.savea(a)
        self.assertFalse(self.verify()['science_verified'])

class MalformedManifestRegression(unittest.TestCase):
 def setUp(self):
    self.fixture=BindingRegression(methodName='test_valid_baseline')
    self.fixture.setUp()
 def tearDown(self):self.fixture.tearDown()
 def test_manifest_wrong_container_rejected(self):
    self.fixture.m.write_text(json.dumps([]))
    with self.assertRaisesRegex(FigureEvidenceError,'MANIFEST_SCHEMA_UNSUPPORTED'):
        self.fixture.verify()
 def test_assets_wrong_container_rejected(self):
    self.fixture.a.write_text(json.dumps([]))
    with self.assertRaisesRegex(FigureEvidenceError,'COMPATIBLE_ASSET_MANIFEST_INVALID'):
        self.fixture.verify()
 def test_assets_with_nonobject_record_rejected(self):
    a=self.fixture.loada();a['assets']=['malformed'];self.fixture.savea(a)
    with self.assertRaisesRegex(FigureEvidenceError,'ASSET_MANIFEST_BINDING_DRIFT'):
        self.fixture.verify()

if __name__=="__main__":unittest.main()
