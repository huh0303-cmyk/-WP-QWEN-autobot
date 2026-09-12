import ast
from pathlib import Path
import re
from scripts.article_seo_repair import metadata_feedback


def test_long_meta_and_missing_query_receive_specific_repair():
    issues=metadata_feedback('Choosing a policy','x'*163,'insurance claims')
    assert len(issues)==2
    assert 'insurance claims' in issues[0]
    assert '163' in issues[1]


def test_complete_metadata_needs_no_repair():
    assert not metadata_feedback('Insurance claims documents','x'*140,'insurance claims')


def postprocess():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/autopost_mega.py').read_text(encoding='utf-8'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='postprocess')
    scope={'re':re};exec(compile(ast.Module(body=[node],type_ignores=[]),'postprocess','exec'),scope)
    return scope['postprocess']


def test_postprocessing_preserves_source_years():
    body='<p>The 2024 report compared 2023 and 2025.</p>'
    actual,meta=postprocess()(body,'x'*140,'Article','report','en',1000,lambda _:None)
    assert actual==body


def test_overlong_meta_is_repaired_without_touching_article():
    body='<p>Original facts.</p>';replacement='A'*139+'.'
    actual,meta=postprocess()(body,'x'*163,'Article','report','en',1000,lambda _:replacement)
    assert actual==body and meta==replacement
