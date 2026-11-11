"""Journal/preprint style routing and editable render tests; no article data fabricated as evidence."""
import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
import fitz
from PIL import Image

from sharepack.publication_styles import select_style, detect_publication_hint
from sharepack.common import save, load, digest, ContractError
from sharepack.ingest import inspect_pdf
from sharepack.render import build

class PublicationStyles(unittest.TestCase):
    def test_arxiv_pdf_edition_precedes_later_journal(self):
        d=select_style({"source_type":"preprint","preprint_server":"arXiv",
                        "journal":"Nature Methods", "doi":"10.48550/arXiv.1709.02082"})
        self.assertEqual(d.style_id,"preprint-arxiv")
        self.assertEqual(d.source_type,"preprint")

    def test_known_journals_and_unknown_fallback(self):
        cases={
            "PLOS Computational Biology":"journal-plos-computational-biology",
            "Nature Communications":"journal-nature-communications",
            "Cell Systems":"journal-cell-systems",
            "Research Journal Unknown":"journal-neutral",
        }
        for name,want in cases.items():
            with self.subTest(journal=name):
                self.assertEqual(select_style({"journal":name}).style_id,want)
        self.assertEqual(select_style({}).style_id,"preprint-neutral")
        with self.assertRaisesRegex(ValueError,"SOURCE_TYPE_UNKNOWN"):
            select_style({"source_type":"made_up"})

    def test_source_matched_plos_color_tokens(self):
        from sharepack.publication_styles import PROFILES
        t=PROFILES["journal-plos-computational-biology"]
        self.assertEqual(t["palette"]["bg"],"FFFFFF")
        self.assertEqual(t["palette"]["navy"],"202124")
        self.assertEqual(t["palette"]["royal"],"4675BF")
        self.assertIn("user-provided", "user-provided screenshot evidence")

    def test_pdf_header_is_tentative(self):
        hint=detect_publication_hint("PLOS Computational Biology\nMethods of tissue mapping\n")
        v=select_style({"publication_hint":hint})
        self.assertEqual(v.style_id,"journal-plos-computational-biology")
        self.assertEqual(v.status,"CANDIDATE_REQUIRES_VERIFICATION")
        self.assertEqual(v.selected_from,"pdf_header_hint")
        self.assertEqual(select_style({"publication_hint":detect_publication_hint("arXiv:1709.02082")}).style_id,"preprint-arxiv")

    def test_text_background_contrast(self):
        def luma(h):
            a=[int(h[i:i+2],16)/255 for i in (0,2,4)]
            a=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in a]
            return .2126*a[0]+.7152*a[1]+.0722*a[2]
        from sharepack.publication_styles import PROFILES
        for name,p in PROFILES.items():
            c=p["palette"]
            for bg,fg in (("bg","navy"),("bg","muted"),("light","navy"),("white","navy"),("mint","navy"),("peach","navy")):
                x,y=sorted((luma(c[bg]),luma(c[fg])))
                ratio=(y+.05)/(x+.05)
                self.assertGreaterEqual(ratio,4.5, (name,bg,fg,ratio))

class PublicationRender(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.root=Path(self.t.name)
        self.pdf=self.root/"source.pdf"
        doc=fitz.open(); page=doc.new_page()
        page.insert_text((75,72),"PLOS Computational Biology",fontsize=16)
        page.insert_text((75,600),"Figure 1: example",fontsize=12)
        doc.save(self.pdf);doc.close()
        self.idx=inspect_pdf(self.pdf,self.root/"index")
        self.assertEqual(self.idx["publication_hint"]["journal"],"PLOS Computational Biology")
        imgdir=self.root/"assets";imgdir.mkdir()
        pic=imgdir/"panel.png";Image.new("RGB",(650,370),"white").save(pic)
        self.assets={"contract":"sharepack-figure-assets-v1","source_pdf_sha256":digest(self.pdf),
                     "assets":[{"id":"F1","figure":"Fig. 1","pdf_page":1,"path":"panel.png",
                                "sha256":digest(pic),"source_pdf_sha256":digest(self.pdf),"review_status":"PENDING"}]}
        save(imgdir/"assets.json",self.assets)
        self.story={"contract":"sharepack-story-v1","paper":{"title":"Synthetic styling QA","doi":"10.1371/journal.pcbi.1010000","authors_short":"Test et al."},
                    "pdf_sha256":digest(self.pdf),"profile":"standard","review_status":"PARTIAL",
                    "formal_ready":False,"sources":[{"id":"S","pdf_page":1}],
                    "claims":[{"id":"C","question":"研究问题","method":"对比研究方法",
                               "observation":"观察到不同情况","meaning":"仍需谨慎解读",
                               "limit":"不是实验因果验证","required":True,"source_ids":["S"]}],
                    "cards":[]}
        for i in range(1,9):
            role=["cover","framework","method","finding","finding","comparison","synthesis","limits"][i-1]
            self.story["cards"].append({"order":i,"stage":role,"title":"科研故事卡片 "+str(i),
                   "intro":"用科研图和证据解释问题。",
                   "narrative_role":role,"layout_type":"evidence",
                   "question":"科学问题如何解决","method":"比较方法与证据来源",
                   "observation":"实际研究数据需要核验","interpretation":"统计模型展示",
                   "takeaway":"仅代表工程验证结果","claim_ids":["C"],
                   "figure_asset_ids":["F1"] if i in (3,4) else [],
                   "flow_steps":["研究问题","实验方法","结果","结论"]})
        self.story_path=self.root/"story.json"
        save(self.story_path,self.story)
    def tearDown(self):
        self.t.cleanup()

    def test_pdf_hint_render_and_no_global_leak(self):
        out=self.root/"plos"
        qa=build(self.story_path,self.root/"assets"/"assets.json",out,
                 render_png=False,pdf_index_path=self.root/"index"/"pdf_index.json")
        self.assertTrue(qa["contract_qa"]["valid"])
        self.assertEqual(qa["publication_style"]["style_id"],"journal-plos-computational-biology")
        self.assertEqual(qa["publication_style"]["status"],"CANDIDATE_REQUIRES_VERIFICATION")
        self.assertEqual(load(out/"publication_style.json")["style_id"],"journal-plos-computational-biology")
        editorial_out=self.root/"plos_editorial"
        editorial_qa=build(self.story_path,self.root/"assets"/"assets.json",
            editorial_out,render_png=False,layout_engine="editorial",
            pdf_index_path=self.root/"index"/"pdf_index.json")
        with zipfile.ZipFile(editorial_out/"SharePack_editable.pptx") as z:
            edxml=z.read("ppt/slides/slide1.xml").decode("utf-8")
        self.assertIn("EFEFEF",edxml)
        self.assertIn("282B62",edxml)
        self.assertNotIn("17272C",edxml)
        with zipfile.ZipFile(out/"SharePack_editable.pptx") as z:
            xml=z.read("ppt/slides/slide1.xml").decode("utf-8")
        self.assertIn("FFFFFF",xml)
        self.assertIn("4675BF",xml)
        # The website-gray masthead is specific to the opt-in editorial engine.
        self.assertNotIn("17272C",xml)
        self.assertIn("Arial",xml)
        self.assertIn("SimHei",xml)
        st=copy.deepcopy(self.story)
        st["paper"]["journal"]="Nature Communications"
        save(self.root/"nature_story.json",st)
        second=build(self.root/"nature_story.json",self.root/"assets"/"assets.json",
                     self.root/"nature",render_png=False)
        self.assertEqual(second["publication_style"]["style_id"],"journal-nature-communications")
        with zipfile.ZipFile(self.root/"nature"/"SharePack_editable.pptx") as z:
            xml2=z.read("ppt/slides/slide1.xml").decode("utf-8")
        self.assertIn("1B222A",xml2)
        self.assertNotIn("EFEFEF",xml2)
        # Original first output does not change when the next run selects another journal.
        self.assertEqual(load(out/"publication_style.json")["style_id"],"journal-plos-computational-biology")

    def test_logo_requires_documented_rights_and_exact_source(self):
        # The test mark is a synthetic placeholder; never a real journal mark.
        logo=self.root/"test_mark.png"
        Image.new("RGB",(320,96),(90,90,90)).save(logo)
        sha=digest(logo)
        manifest={"contract":"sharepack-journal-logo-v1",
            "style_id":"journal-plos-computational-biology",
            "doi":"10.1371/journal.pcbi.1010000",
            "source_type":"journal",
            "publisher_name":"TEST ONLY — NOT PLOS",
            "source_url":"https://example.org/fixture-test-mark",
            "permission_evidence_url":"https://example.org/fixture-license",
            "rights_basis":"written_permission",
            "original_sha256":sha,"file":"test_mark.png"}
        save(self.root/"logo.json",manifest)
        st=copy.deepcopy(self.story)
        st["paper"]["journal"]="PLOS Computational Biology"
        st["paper"]["source_type"]="journal"
        save(self.story_path,st)
        qa=build(self.story_path,self.root/"assets"/"assets.json",self.root/"withlogo",
                 render_png=False,logo_manifest_path=self.root/"logo.json")
        self.assertEqual(qa["publication_logo"]["status"],"DISPLAYED_WITH_DOCUMENTED_PERMISSION")
        self.assertEqual(qa["publication_logo"]["original_sha256"],sha)
        from pptx import Presentation
        deck=Presentation(self.root/"withlogo"/"SharePack_editable.pptx")
        self.assertTrue(any(sh.shape_type==13 for sh in deck.slides[0].shapes))
        # Explicitly missing rights must fail closed.
        manifest["rights_basis"]="none"
        save(self.root/"logo_bad.json",manifest)
        with self.assertRaisesRegex(ContractError,"LOGO_PERMISSION_NOT_DOCUMENTED"):
            build(self.story_path,self.root/"assets"/"assets.json",self.root/"reject",
                  render_png=False,logo_manifest_path=self.root/"logo_bad.json")
        # Publisher mismatch and byte drift are also blocking.
        manifest["rights_basis"]="written_permission"
        manifest["style_id"]="journal-nature-communications"
        save(self.root/"logo_wrong.json",manifest)
        with self.assertRaisesRegex(ContractError,"LOGO_PUBLICATION_STYLE_MISMATCH"):
            build(self.story_path,self.root/"assets"/"assets.json",self.root/"reject2",
                  render_png=False,logo_manifest_path=self.root/"logo_wrong.json")
        manifest["style_id"]="journal-plos-computational-biology"
        manifest["original_sha256"]="0"*64
        save(self.root/"logo_drift.json",manifest)
        with self.assertRaisesRegex(ContractError,"LOGO_HASH_MISMATCH"):
            build(self.story_path,self.root/"assets"/"assets.json",self.root/"reject3",
                  render_png=False,logo_manifest_path=self.root/"logo_drift.json")

    def test_preprint_cannot_be_rebranded_with_journal_logo(self):
        logo=self.root/"pretend.png";Image.new("RGB",(320,96),"grey").save(logo)
        manifest={"contract":"sharepack-journal-logo-v1",
          "style_id":"journal-plos-computational-biology",
          "source_type":"journal",
          "doi":"10.1371/journal.pcbi.1010000",
          "publisher_name":"TEST ONLY",
          "source_url":"https://example.org/test",
          "permission_evidence_url":"https://example.org/perm",
          "rights_basis":"written_permission",
          "file":logo.name,"original_sha256":digest(logo)}
        save(self.root/"wrong_edition.json",manifest)
        st=copy.deepcopy(self.story)
        st["paper"]["source_type"]="preprint"
        st["paper"]["preprint_server"]="arXiv"
        save(self.story_path,st)
        with self.assertRaisesRegex(ContractError,"LOGO_PUBLICATION_STYLE_MISMATCH"):
            build(self.story_path,self.root/"assets"/"assets.json",self.root/"reject_preprint",
                  render_png=False,logo_manifest_path=self.root/"wrong_edition.json")

    def test_source_index_hash_mismatch_rejected(self):
        bad=copy.deepcopy(self.idx);bad["pdf_sha256"]="z"*64
        save(self.root/"bad_index.json",bad)
        with self.assertRaisesRegex(ContractError,"PUBLICATION_INDEX_PDF_HASH_MISMATCH"):
            build(self.story_path,self.root/"assets"/"assets.json",self.root/"bad",
                  render_png=False,pdf_index_path=self.root/"bad_index.json")

if __name__=="__main__":unittest.main()
