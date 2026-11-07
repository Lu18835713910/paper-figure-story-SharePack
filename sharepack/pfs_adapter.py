"""Read-only PFS 1.1 bridge. Scientific facts and original PFS files are immutable.

The bridge deliberately emits references, not a supposedly reviewed science story.
Every output stays outside the source PFS tree, and claims must bind to intact source.
"""
from pathlib import Path
import shutil
from .common import ContractError, load, save, digest, within

SUPPORTED_SCHEMA={'1.1'}
RELATIONS={'data_depends_on','experimental_precedes','parallel_branch','independent_validation',
           'evidence_supports','compares','argument_transition','optional_path','integrates'}
REVIEW_KEYS=('figure_identity','crop_complete','axes_legends_scalebars',
             'significance_marks','readability')
REVIEW_BINDINGS=('sha256','source_sha256','physical_page','crop',
                 'evidence_ids','figure_id','source_document_id','panels')

def _review_complete(asset):
    review=asset.get('visual_review') or {}
    return (review.get('status')=='pass' and bool(review.get('reviewer'))
            and all(review.get(k) is True for k in REVIEW_KEYS)
            and all(review.get(k)==asset.get(k) for k in REVIEW_BINDINGS))


def _unmodified_source_output(src, outdir):
    src=Path(src).resolve()
    dest=Path(outdir).resolve()
    if dest == src.parent or dest.is_relative_to(src.parent):
        # PFS outputs often live in a run directory; avoid writing alongside inputs.
        raise ContractError('PFS_OUTPUT_INSIDE_SOURCE_TREE')
    return src,dest


def _load_pfs(knowledge_path):
    kp=Path(knowledge_path).resolve()
    model=load(kp)
    ver=str(model.get('schema_version',model.get('knowledge_schema_version','')))
    if ver not in SUPPORTED_SCHEMA:
        raise ContractError(f'PFS_SCHEMA_UNSUPPORTED:{ver!r}; expected 1.1')
    mandatory=('document_registry','entities','figures','stories','relations')
    for key in mandatory:
        if not isinstance(model.get(key),list):
            raise ContractError('PFS_MODEL_INVALID:'+key)
    idx={}; all_ids=set()
    for key in mandatory:
        ids=[]
        for item in model[key]:
            if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id']:
                raise ContractError('PFS_ID_INVALID:'+key)
            ids.append(item['id'])
        if len(ids)!=len(set(ids)) or all_ids.intersection(ids):
            raise ContractError('PFS_DUPLICATE_GLOBAL_ID:'+key)
        idx[key]=set(ids);all_ids.update(ids)
    if not model['stories']:raise ContractError('PFS_STORIES_EMPTY')
    for story in model['stories']:
        for f in story.get('figure_refs',[]):
            if f not in idx['figures']:raise ContractError('PFS_UNRESOLVED_FIGURE:'+str(f))
        for key in ('method_ids','evidence_ids'):
            for entity in story.get(key,[]):
                if entity not in idx['entities']:
                    raise ContractError('PFS_UNRESOLVED_ENTITY:'+str(entity))
    for f in model['figures']:
        if f.get('document_id') and f['document_id'] not in idx['document_registry']:
            raise ContractError('PFS_FIGURE_DOCUMENT_UNKNOWN:'+f['id'])
    for rel in model['relations']:
        if rel.get('from') not in idx['entities'] or rel.get('to') not in idx['entities']:
            raise ContractError('PFS_RELATION_END_MISSING:'+rel['id'])
        if rel.get('type') not in RELATIONS:
            raise ContractError('PFS_RELATION_TYPE_UNSUPPORTED:'+str(rel.get('type')))
        if rel.get('from')==rel.get('to'):
            raise ContractError('PFS_RELATION_SELF_EDGE:'+rel['id'])
        if rel.get('certainty')=='presentation_only' and (rel.get('type')!='argument_transition' or rel.get('provenance')!='presentation'):
            raise ContractError('PFS_RELATION_SEMANTICS_INVALID:'+rel['id'])
        if rel.get('type')=='experimental_precedes' and (rel.get('certainty')!='paper_reported' or not rel.get('order_basis')):
            raise ContractError('PFS_EXPERIMENTAL_ORDER_UNVERIFIED:'+rel['id'])
    return kp,model,ver,idx


def _normalise_asset_manifest(obj, model, crosswalk=None):
    """Read two *explicit* PFS formats. This is a source-preserving compatibility view.

    This routine never turns a missing evidence link or pending visual check into a
    scientific fact. Unlike a filename-based migration it uses the knowledge IDs.
    """
    ver = obj.get('asset_version') or obj.get('version')
    if ver not in ('m2b-1', 'pfs-figure-assets-1') or not isinstance(obj.get('assets'),list):
        raise ContractError('PFS_ASSET_VERSION_UNSUPPORTED:'+str(ver))
    docs={x['id']:x for x in model['document_registry']}
    figures={x['id']:x for x in model['figures']}
    result=[];seen=set();warnings=[]
    crosswalk=crosswalk or {}
    for item in obj['assets']:
        a=dict(item);aid=a.get('id')
        if not isinstance(aid,str) or not aid or aid in seen:raise ContractError('PFS_ASSET_ID_INVALID')
        seen.add(aid)
        x=crosswalk.get(aid,{})
        if a.get('figure_id') and x.get('figure_id') and a['figure_id']!=x['figure_id']:
            raise ContractError('PFS_CROSSWALK_FIGURE_CONFLICT:'+aid)
        fid=a.get('figure_id') or x.get('figure_id')
        if not fid:
            raise ContractError('PFS_ASSET_FIGURE_ID_REQUIRED_CROSSWALK:'+aid)
        a['figure_id']=fid
        if not a.get('source_document_id') and x.get('source_document_id'):
            a['source_document_id']=x['source_document_id']
        if 'evidence_ids' not in a and 'evidence_ids' in x:
            a['evidence_ids']=x['evidence_ids']
        if fid not in figures:raise ContractError('PFS_ASSET_FIGURE_UNKNOWN:'+str(fid))
        fig=figures[fid]
        d=a.get('source_document_id') or fig.get('document_id')
        if d not in docs or d!=fig.get('document_id'):
            raise ContractError('PFS_ASSET_DOCUMENT_BINDING_MISMATCH:'+str(fid))
        a['source_document_id']=d
        a['source_sha256']=a.get('source_sha256') or a.get('source_pdf_sha256')
        expected=docs[d].get('sha256')
        if expected and a.get('source_sha256')!=expected:
            raise ContractError('PFS_ASSET_SOURCE_HASH_MISMATCH:'+str(fid))
        # No new scientific identity is invented. Only known story evidence can bind.
        linked=[st for st in model['stories'] if fid in st.get('figure_refs',[])]
        linked_evidence=set().union(*(set(st.get('evidence_ids',[])) for st in linked)) if linked else set()
        evidence=a.get('evidence_ids')
        if evidence is None:evidence=sorted(linked_evidence)
        else:
            if not set(evidence)<=linked_evidence:
                raise ContractError('PFS_ASSET_EVIDENCE_STORY_MISMATCH:'+str(aid))
        a['evidence_ids']=list(evidence)
        if not a['evidence_ids']:
            # A figure can be an author interpretation/model. No fabricated E ID.
            a['evidence_role']='UNBOUND_FIGURE_REQUIRES_REVIEW'
            warnings.append('UNBOUND_FIGURE:'+str(fid))
        else:
            a['evidence_role']='LINKED_EVIDENCE'
        # Normalised provenance retains both legacy and canonical fields.
        a['pfs_asset_contract']=ver
        if 'crop_pdf_pt' not in a and a.get('bbox_pt') is not None:
            a['crop_pdf_pt']=a['bbox_pt']
        if a.get('visual_review') is None:
            a['visual_review']={'status':'pending', 'legacy_status':a.get('visual_status',a.get('semantic_review_status','PENDING'))}
        result.append(a)
    return {'asset_version':'m2b-1','source_contract':ver,'assets':result}, sorted(set(warnings))


def _check_asset_manifest(assets_path,model,crosswalk_path=None,knowledge_path=None):
    if not assets_path:return None,None,None
    ap=Path(assets_path).resolve();raw=load(ap)
    crosswalk={}
    if crosswalk_path:
        cp=Path(crosswalk_path).resolve();view=load(cp)
        if view.get('contract')!='sharepack-pfs-asset-crosswalk-v1':
            raise ContractError('PFS_CROSSWALK_CONTRACT_INVALID')
        if view.get('asset_manifest_sha256')!=digest(ap):
            raise ContractError('PFS_CROSSWALK_ASSET_MANIFEST_DRIFT')
        if knowledge_path and view.get('knowledge_sha256')!=digest(knowledge_path):
            raise ContractError('PFS_CROSSWALK_KNOWLEDGE_DRIFT')
        entries=view.get('mapping',[])
        if not isinstance(entries,list) or any(not x.get('asset_id') for x in entries) or len({x['asset_id'] for x in entries})!=len(entries):
            raise ContractError('PFS_CROSSWALK_IDS_INVALID')
        crosswalk={x['asset_id']:x for x in entries}
        if not set(crosswalk)<={x.get('id') for x in raw.get('assets',[])}:
            raise ContractError('PFS_CROSSWALK_UNKNOWN_ASSET')
    obj,notes=_normalise_asset_manifest(raw,model,crosswalk)
    missing=[];reviewed=0
    for a in obj['assets']:
        aid=a['id']
        # Only exact original M2B proof, not legacy free-form status, can count as reviewed.
        if a['pfs_asset_contract']=='m2b-1' and _review_complete(a):reviewed+=1
        review=a.get('visual_review') or {}
        if not a.get('path'):
            missing.append(aid)
            if review.get('status')=='pass':raise ContractError('PFS_REVIEWED_ASSET_PATH_MISSING:'+aid)
            continue
        candidate=Path(a['path']);path=candidate if candidate.is_absolute() else ap.parent/candidate
        if not path.is_file():
            missing.append(aid)
            if review.get('status')=='pass':raise ContractError('PFS_REVIEWED_ASSET_FILE_MISSING:'+aid)
        elif not a.get('sha256'):
            raise ContractError('PFS_ASSET_HASH_REQUIRED:'+aid)
        elif digest(path)!=a['sha256']:
            raise ContractError('PFS_ASSET_FILE_HASH_MISMATCH:'+aid)
    summary={'path':str(ap),'sha256':digest(ap),'count':len(obj['assets']),
        'source_asset_contract':obj['source_contract'],'reviewed_by_record':reviewed,
        'unavailable_asset_ids':missing,'diagnostics':notes,'formal_ready':False,
        'note':'Legacy visual statuses never imply independent Figure/panel review.'}
    return ap,obj,summary


def bridge(knowledge_path,outdir,assets_path=None,crosswalk_path=None):
    kp,outdir=_unmodified_source_output(knowledge_path,outdir)
    kp,model,ver,idx=_load_pfs(kp)
    ap,manifest,summary=_check_asset_manifest(assets_path,model,crosswalk_path,kp)
    docs=[{'id':d['id'],'role':d.get('role'),'sha256':d.get('sha256'),
           'availability':d.get('availability'),'format':d.get('format')} for d in model['document_registry']]
    figs=[{'id':f['id'],'document_id':f.get('document_id'),'kind':f.get('kind')} for f in model['figures']]
    rsus=[{'rsu_id':st['id'],'presentation_order':st.get('presentation_order'),
           'original_section_order':st.get('original_section_order'),
           'restructuring_reason':st.get('restructuring_reason'),
           'question_or_purpose':st.get('question_or_purpose'),
           'finding_or_argument':st.get('finding_or_argument'),
           'limits':st.get('limits'),
           'method_ids':st.get('method_ids',[]),'evidence_ids':st.get('evidence_ids',[]),
           'figure_ids':st.get('figure_refs',[]),
           'question_refs':st.get('question_refs',[]), 'finding_refs':st.get('finding_refs',[]),
           'source_refs':st.get('source_refs',[]),
           'source_ref_count':len(st.get('source_refs',[]))}
          for st in model['stories']]
    edges=[{k:r.get(k) for k in ('id','from','to','type','certainty','provenance','mandatory','order_basis')}
           for r in model['relations']]
    context={'contract':'sharepack-pfs-bridge-v1','source_kind':'PFS_M1_1.1',
       'knowledge_file':str(kp),'knowledge_sha256':digest(kp),'pfs_knowledge_schema_version':ver,
       'documents':docs,'figures':figs,'asset_summary':summary,'rsus':rsus,'relations':edges,
       'diagnostics':{'source_review':'NOT_PERFORMED_BY_BRIDGE',
         'scientific_story':'REQUIRES_AGENT_TRANSLATION','formal_ready':False,
         'unknown_relation_types':[],
         'notice':'Only identities are imported. No scientific claim or causal arrow is generated.'}}
    if digest(kp)!=context['knowledge_sha256'] or (ap and digest(ap)!=summary['sha256']):
        raise ContractError('PFS_SOURCE_CHANGED_DURING_BRIDGE')
    if crosswalk_path:
        context['crosswalk_sha256']=digest(crosswalk_path)
        context['crosswalk_file']=str(Path(crosswalk_path).resolve())
    if (outdir/'pfs_bridge_context.json').exists():
        raise ContractError('OUTPUT_ALREADY_EXISTS_USE_NEW_DIRECTORY')
    out=save(outdir/'pfs_bridge_context.json',context)
    return out,context


def verify_bridge_context(context_path):
    """Rehash live upstream PFS inputs at the moment SharePack uses a bridge."""
    ctx=load(context_path)
    if ctx.get('contract')!='sharepack-pfs-bridge-v1':raise ContractError('PFS_BRIDGE_SCHEMA_UNSUPPORTED')
    src=ctx.get('knowledge_file')
    if not src or not Path(src).is_file():raise ContractError('PFS_ORIGINAL_KNOWLEDGE_UNAVAILABLE')
    if digest(src)!=ctx.get('knowledge_sha256'):
        raise ContractError('PFS_ORIGINAL_KNOWLEDGE_DRIFT')
    if ctx.get('asset_summary'):
        a=ctx['asset_summary'];path=Path(a.get('path',''))
        if not path.is_file():raise ContractError('PFS_ORIGINAL_ASSET_MANIFEST_UNAVAILABLE')
        if digest(path)!=a.get('sha256'):
            raise ContractError('PFS_ORIGINAL_ASSET_MANIFEST_DRIFT')
        _,model,_,_=_load_pfs(src)
        crosswalk_file=ctx.get('crosswalk_file')
        if crosswalk_file:
            if not Path(crosswalk_file).is_file() or digest(crosswalk_file)!=ctx.get('crosswalk_sha256'):
                raise ContractError('PFS_CROSSWALK_CHANGED')
        _check_asset_manifest(path,model,crosswalk_file,src)   # Recheck originals, not cached bridge
    return ctx


def import_assets(knowledge_path,assets_path,outdir,crosswalk_path=None):
    """Copy original, SHA-verified PFS figures into an isolated SharePack asset package.

    This never makes an image visually reviewed merely because it was registered.
    """
    kp,outdir=_unmodified_source_output(knowledge_path,outdir)
    kp,model,ver,idx=_load_pfs(kp)
    ap,original,summary=_check_asset_manifest(assets_path,model,crosswalk_path,kp)
    if summary['unavailable_asset_ids']:
        raise ContractError('PFS_SOURCE_ASSETS_UNAVAILABLE:'+','.join(summary['unavailable_asset_ids']))
    if outdir.exists() and any(outdir.iterdir()):
        raise ContractError('OUTPUT_ALREADY_EXISTS_USE_NEW_DIRECTORY')
    # Store original source PDF binding only if there is exactly one primary PDF.
    pdfs={a['source_sha256'] for a in original['assets'] if a.get('source_sha256')}
    if len(pdfs)!=1:raise ContractError('PFS_MULTIPLE_SOURCE_PDFS_REQUIRE_SELECTION')
    sha=next(iter(pdfs));srcs=[]
    for a in original['assets']:
        p=Path(a['path']);p=p if p.is_absolute() else ap.parent/p
        if not p.is_file() or digest(p)!=a.get('sha256'):
            raise ContractError('PFS_SOURCE_IMAGE_UNAVAILABLE_OR_DRIFT:'+a['id'])
        srcs.append((a,p))
    if any(p.suffix.lower()!='.png' for _,p in srcs):
        raise ContractError('PFS_UNSUPPORTED_IMAGE_TYPE')
    outdir.mkdir(parents=True,exist_ok=True)
    copied=[]
    for i,(a,p) in enumerate(srcs,1):
        path=outdir/'assets'/f'pfsa_{i:03}.png'
        # Keep the original pixels byte-for-byte when PNG. Other image types not guessed.
        if p.suffix.lower()!='.png':
            raise ContractError('PFS_UNSUPPORTED_IMAGE_TYPE:'+str(p.suffix))
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,path)
        if digest(path)!=a['sha256']:raise ContractError('PFS_COPIED_ASSET_DRIFT:'+a['id'])
        review=a.get('visual_review') or {}
        is_reviewed=(a.get('pfs_asset_contract')=='m2b-1' and _review_complete(a))
        copied.append({'id':'pfsa_'+str(i).zfill(3),'figure':a['figure_id'],
           'pdf_page':a.get('physical_page'),'crop_normalized':a.get('crop'),
           'crop_pdf_pt':a.get('crop_pdf_pt'),'path':str(path.relative_to(outdir)),'sha256':a['sha256'],
           'source_pdf_sha256':sha,'review_status':'VISUAL_REVIEWED' if is_reviewed else 'PENDING',
           'pfs_asset_id':a['id'],'pfs_evidence_ids':a['evidence_ids'],
           'evidence_role':a['evidence_role'],'pfs_source_contract':a['pfs_asset_contract'],
           'source_document_id':a['source_document_id'],'license_note':'PFS registered source; verify rights before publication'})
    result={'contract':'sharepack-figure-assets-v1','source_pdf_name':None,
            'source_pdf_sha256':sha,'assets':copied,'original_data_unchanged':True,
            'pfs_assets_sha256':digest(ap),'pfs_knowledge_sha256':digest(kp),
            'diagnostics':summary['diagnostics']}
    save(outdir/'assets.json',result)
    return result
