"""Validate a source-bound editorial handoff before rendering."""
from .common import ContractError, digest, load
from .logic_ab import _ab_model
from .pfs_adapter import _check_asset_manifest, _load_pfs, verify_bridge_context


def validate_handoff(story, assets):
    binding = story.get('research_logic')
    if not binding:
        return
    path, model, nodes, edges = _ab_model(binding['path'])
    if digest(path) != binding['sha256'] or model['snapshot'] != binding['snapshot']:
        raise ContractError('EDITORIAL_LOGIC_DRIFT')
    network = load(model['inputs']['network']['path'])
    context = verify_bridge_context(story['pfs_bridge']['context_path'])
    network_m1 = next(x for x in network['inputs'] if x['kind'] == 'knowledge')
    if network_m1['sha256'] != context['knowledge_sha256']:
        raise ContractError('EDITORIAL_LOGIC_M1_MISMATCH')
    rsus = {x['rsu_id'] for x in context['rsus']}
    _, m1, _, _ = _load_pfs(context['knowledge_file'])
    manifest = context['asset_summary']['path']
    _, registered, _ = _check_asset_manifest(manifest, m1, context.get('crosswalk_file'), context['knowledge_file'])
    registered = {a['id']: a for a in registered['assets']}
    indexed = {x['id']:x for x in assets['assets']}
    branches = {b['id']: b for b in model['branches']}
    used_branches = set()
    core_nodes, core_edges = set(), set()
    for card in story['cards']:
        source = card['logic_sources']
        selected = set(source['nodes'])
        if not selected or not selected <= nodes.keys() or not set(source['rsus']) <= rsus:
            raise ContractError('EDITORIAL_LOGIC_UNKNOWN_NODE_OR_RSU')
        for rid in source['relations']:
            r = edges.get(rid)
            if not r or not {r['from'], r['to']} <= selected:
                raise ContractError('EDITORIAL_LOGIC_EDGE_ENDPOINT_MISMATCH')
        elements = card['editorial']['elements']
        drawn_nodes = {e['node_id'] for e in elements if e['kind'] == 'logic_node'}
        drawn_edges = {e['relation_id'] for e in elements if e['kind'] == 'logic_edge'}
        if not drawn_nodes <= selected or not drawn_edges <= set(source['relations']):
            raise ContractError('EDITORIAL_LOGIC_UNDECLARED_ELEMENT')
        for aid in card['figure_asset_ids']:
            a = indexed[aid]
            rsu_figures = {f for r in context['rsus'] if r['rsu_id'] in source['rsus'] for f in r['figure_ids']}
            original = registered.get(a.get('pfs_asset_id'))
            if not original or a['sha256'] != original['sha256'] or a['figure'] not in rsu_figures:
                raise ContractError('EDITORIAL_LOGIC_FIGURE_RSU_MISMATCH')
        branch_id = source.get('branch')
        if branch_id is not None:
            branch = branches.get(branch_id)
            if not branch or not set(source['relations']).intersection(branch['edges']):
                raise ContractError('EDITORIAL_LOGIC_BRANCH_MISMATCH')
            used_branches.add(branch_id)
        if source.get('scope') == 'A':
            core_nodes.update(drawn_nodes)
            core_edges.update(drawn_edges)
        for element in elements:
            if element['kind'] == 'logic_node':
                node = nodes[element['node_id']]
                element['source_text'] = node.get('short_text') or node['title']
            if element['kind'] == 'logic_edge':
                edge = edges[element['relation_id']]
                element['relation_type'] = edge['type']
                element['source'] = edge['from']
                element['target'] = edge['to']
        source['snapshot'] = model['snapshot']
        source['figures'] = [indexed[aid] for aid in card['figure_asset_ids']]
        source['pdf_sha256'] = story['pdf_sha256']
    if used_branches != set(branches):
        raise ContractError('EDITORIAL_LOGIC_BRANCH_OMITTED')
    if core_nodes != set(model['core']['nodes']) or core_edges != set(model['core']['edges']):
        raise ContractError('EDITORIAL_LOGIC_INCOMPLETE_A')
