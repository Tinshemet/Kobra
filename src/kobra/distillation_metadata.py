"""Lossless text accounting and caller annotations, never deletion authority."""
from copy import deepcopy
import json
import re

CATEGORIES = {'garbage', 'noise', 'social', 'unclassified', 'unresolved'}


def describe_text(source, points, relations, result, caller_metadata=None, annotations=()):
    if caller_metadata is not None and not isinstance(caller_metadata, dict):
        raise ValueError('metadata must be a JSON object')
    try:
        caller = json.loads(json.dumps(caller_metadata or {}, allow_nan=False))
    except (ValueError, TypeError) as exc:
        raise ValueError('metadata must contain finite JSON data') from exc
    # Evidence coverage is not a claim that every covered word was interpreted.
    intervals = [(e['start'],e['end'],p['id']) for p in points for e in p['evidence']]
    boundaries = sorted({0,len(source),*(a for a,b,p in intervals),*(b for a,b,p in intervals)})
    accounting = []
    for a,b in zip(boundaries,boundaries[1:]):
        if a==b:continue
        text=source[a:b];owners=sorted({p for x,y,p in intervals if x<=a and b<=y})
        if owners:category='point_evidence';reason='covered_by_point_evidence_not_semantic_completeness'
        elif text.isspace():category='formatting';reason='whitespace_only'
        elif re.fullmatch(r'[\s.,;:!?]+',text):category='surface_syntax';reason='punctuation_retained_for_scope_and_sentence_form'
        elif relations and re.fullmatch(r'[\s,;]*(?:and(?:\s+then)?|then)[\s,;]*',text,re.I):
            category='connector';reason='source_connector_with_recorded_relation'
        else:
            category='unresolved' if not points else 'unclassified'
            reason='no_supported_points' if not points else 'no_deterministic_classification'
        accounting.append(dict(source_id='request',start=a,end=b,text=text,category=category,
                               reason=reason,point_ids=owners,retained=True))
    buckets={k:[] for k in sorted(CATEGORIES)}
    for item in accounting:
        if item['category'] in buckets:buckets[item['category']].append(deepcopy(item))
    recorded=[]
    for item in annotations:
        if not isinstance(item,dict):raise ValueError('annotation must be an object')
        a,b=item.get('start'),item.get('end');category=item.get('category')
        if (type(a) is not int or type(b) is not int or not 0<=a<b<=len(source)
                or item.get('text')!=source[a:b] or category not in CATEGORIES
                or not isinstance(item.get('reason'),str) or not item['reason'].strip()
                or not isinstance(item.get('provenance'),str) or not item['provenance'].strip()):
            raise ValueError('annotation requires exact source span, category, reason and provenance')
        entry=dict(source_id='request',start=a,end=b,text=source[a:b],category=category,
            reason=item['reason'],provenance=item['provenance'],status='caller_annotation_not_semantically_verified',
            retained=True,overlaps_point_evidence=any(a<y and x<b for x,y,p in intervals))
        recorded.append(entry);buckets[category].append(deepcopy(entry))
    code=result.get('code_proposal',{})
    metadata=dict(producer='kobra',read_version=code.get('version'),read_configuration_id=code.get('configuration_id'),
        assignment_source=result.get('assignment_source'),
        generative_assignment_used=result.get('assignment_source')=='AI',
        offset_unit='unicode_code_points',point_count=len(points),relation_count=len(relations),
        source_characters=len(source),accounted_characters=sum(x['end']-x['start'] for x in accounting),
        discarded_characters=0,semantic_coverage='not_measured',
        caller=caller,caller_metadata_authority='descriptive_only_not_grounding_or_routing_authority')
    open_items=[]
    for origin,reasons in [('gate',result.get('reasons',[])),('parser',code.get('reasons',[]))]:
        for reason in reasons:
            if origin=='parser':kind='parsing'
            elif reason.startswith('missing_context:'):kind='missing_context'
            elif reason.startswith(('memory_','ungrounded_reference','unresolved_reference','unresolved_local_reference')):kind='reference_resolution'
            elif reason.startswith('knowledge_'):kind='knowledge'
            elif 'cohort' in reason or 'calibration' in reason:kind='calibration'
            else:kind='validation'
            open_items.append(dict(kind=kind,reason=reason,origin=origin,status='open'))
    return metadata,dict(partition=accounting,annotations=recorded,open_items=open_items,**buckets,
        policy='Preserve all text. Unclassified does not mean garbage. Annotations cannot alter points, grounding or gate status.')
