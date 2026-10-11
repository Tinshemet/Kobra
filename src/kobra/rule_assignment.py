"""Experimental deterministic role assignment over a learned dependency parser.

No gold, sentence inventory or generative model is consulted. Rule eligibility
is not calibrated confidence. Original text always accompanies the proposal.
"""
from .selection_read import SLOTS

VERSION = 'rule-assignment-3'

class RuleAssigner:
    def __init__(self, nlp=None, action_words=None):
        if nlp is None:
            import spacy
            nlp = spacy.load('en_core_web_sm')
        self.nlp = nlp
        from .surface_chunks import ACTIONS
        self.action_words = ACTIONS if action_words is None else frozenset(action_words)

    def assign(self, text):
        from .surface_chunks import chunk_commands
        boundaries = chunk_commands(text, self.action_words)
        simple = self._assign_simple(text)
        simple['surface_structure'] = boundaries
        if simple['route'] == 'code':
            # The simple parser is not allowed to swallow an explicit command
            # boundary or ignore unbalanced protected text.
            if len(boundaries['chunks']) <= 1 and not any(
                    issue in boundaries['issues'] for issue in ('unmatched_bracket','unclosed_quote_or_bracket')):
                return simple
        from .structural_read import assign_structure
        structured = assign_structure(self.nlp(text), boundaries)
        if structured is not None:
            structured['surface_structure'] = boundaries
            return structured
        if simple['route'] == 'code':
            simple.update(route='unresolved', reasons=['unsupported_surface_structure'])
        return simple

    def _assign_simple(self, text):
        doc = self.nlp(text)
        out = dict(source=text, frames=[], route='unresolved', rules=[], reasons=[],
                   semantic_verified=False, version=VERSION)
        def stop(reason):
            out['reasons'].append(reason)
            return out
        if len(list(doc.sents)) != 1:
            return stop('requires one sentence')
        if any(t.dep_ in {'conj','relcl','advcl','ccomp','xcomp','parataxis'} for t in doc):
            return stop('multiple predicates or clause attachment')
        root = next((t for t in doc if t.dep_ == 'ROOT'), None)
        if root is None or root.pos_ not in {'VERB','AUX'}:
            return stop('no supported predicate')
        if any(t.pos_ == 'VERB' and t != root for t in doc):
            return stop('additional lexical verb')
        # Only complete, contiguous noun chunks; do not guess attachment.
        chunks = {c.root.i:c for c in doc.noun_chunks}
        def phrase(t):
            c = chunks.get(t.i)
            return c.text if c is not None else (t.text if t.pos_ == 'PRON' else None)
        frame = {s:'NONE' for s in SLOTS}
        frame['act'] = 'question' if text.rstrip().endswith('?') else 'assertion'
        frame['predicate'] = root.text
        subjects = [t for t in root.children if t.dep_ in {'nsubj','nsubjpass'}]
        objects = [t for t in root.children if t.dep_ in {'dobj','obj'}]
        recipients = [t for t in root.children if t.dep_ == 'dative']
        if max(len(subjects),len(objects),len(recipients)) > 1:
            return stop('multiple role candidates')
        passive = any(t.dep_ == 'auxpass' for t in root.children) or any(t.dep_=='nsubjpass' for t in subjects)
        if passive:
            if not subjects: return stop('passive without subject')
            frame['patient'] = phrase(subjects[0])
            agents = [t for t in root.children if t.dep_ == 'agent' and t.lower_ == 'by']
            if len(agents)>1: return stop('multiple by phrases')
            if agents:
                actor = [t for t in agents[0].children if t.dep_=='pobj']
                if len(actor)!=1: return stop('unresolved by phrase')
                frame['agent'] = phrase(actor[0])
            out['rules'].append('C001-passive-roles')
        else:
            if subjects: frame['agent'] = phrase(subjects[0])
            elif root.tag_ == 'VB' and frame['act'] != 'question': frame['act']='request'
            else: return stop('missing subject or uncertain imperative')
            if objects: frame['patient'] = phrase(objects[0])
            if recipients: frame['recipient'] = phrase(recipients[0])
            out['rules'].append('C002-active-roles')
        if root.lemma_ == 'be':
            states = [t for t in root.children if t.dep_=='acomp' and t.pos_=='ADJ']
            if len(states)!=1: return stop('unsupported copular complement')
            frame['predicate']=states[0].text
            out['rules'].append('C003-adjective-state')
        if any(v is None for v in frame.values()):return stop('incomplete noun phrase')
        if any(t.dep_=='prep' for t in doc): return stop('unresolved prepositional attachment')
        neg = [t for t in doc if t.dep_=='neg']
        modals = [t for t in doc if t.tag_=='MD']
        if len(neg)>1 or len(modals)>1:return stop('multiple scope operators')
        if neg:frame['negation']=neg[0].text
        if modals:frame['modality']=modals[0].text
        # Quantified and adverbial constructions remain unresolved in v1.
        if any(t.dep_ in {'nummod','npadvmod'} or t.lower_ in {'all','every','each','some','any','no','both','many','few'} for t in doc):
            return stop('quantity or temporal interpretation')
        if any(t.dep_=='advmod' and t.lower_ not in {'very','not'} for t in doc):
            return stop('adverbial interpretation')
        out.update(frames=[frame],route='code',reasons=[])
        return out

    def read(self, text, fallback=None):
        proposal = self.assign(text)
        if proposal['route']=='unresolved' and fallback is not None:
            # Preserve both provenance and uncertainty; a fallback is not proof.
            proposal['fallback'] = fallback(text)
            proposal['route'] = 'model_proposal'
        return proposal
