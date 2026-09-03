from scripts.repair_blogger_images import IMG_RE

def test_replaces_only_matching_broken_src():
 html='<p><img src="https://bad/x.webp"><img src="https://good/y.webp"></p>'; bad={'https://bad/x.webp'}
 new=IMG_RE.sub(lambda m:m.group(1)+'https://stable/x.webp'+m.group(3) if m.group(2) in bad else m.group(0),html)
 assert 'https://stable/x.webp' in new and 'https://good/y.webp' in new and 'https://bad/x.webp' not in new

def test_regex_supports_single_and_double_quotes():
 assert len(IMG_RE.findall("<img src='a'><img alt='x' src=\"b\">"))==2
