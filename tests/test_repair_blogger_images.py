from scripts.repair_blogger_images import IMG_RE, is_temporary

def test_replaces_only_matching_broken_src():
 html='<p><img src="https://bad/x.webp"><img src="https://good/y.webp"></p>'; bad={'https://bad/x.webp'}
 new=IMG_RE.sub(lambda m:m.group(1)+'https://stable/x.webp'+m.group(3) if m.group(2) in bad else m.group(0),html)
 assert 'https://stable/x.webp' in new and 'https://good/y.webp' in new and 'https://bad/x.webp' not in new

def test_regex_supports_single_and_double_quotes():
 assert len(IMG_RE.findall("<img src='a'><img alt='x' src=\"b\">"))==2

def test_replicate_urls_are_temporary_even_when_alive():
 assert is_temporary('https://replicate.delivery/x/image.webp')
 assert is_temporary('https://x.replicateusercontent.com/image.webp')
 assert not is_temporary('https://raw.githubusercontent.com/o/r/main/a.webp')

def test_full_inventory_uses_blogger_page_tokens():
 from pathlib import Path
 source=(Path(__file__).resolve().parents[1]/'scripts/repair_blogger_images.py').read_text(encoding='utf-8')
 assert "nextPageToken" in source and "pageToken" in source and "maxResults':500" in source

def test_future_publisher_has_permanent_image_hard_gate():
 from pathlib import Path
 source=(Path(__file__).resolve().parents[1]/'scripts/publish_blogger_33_now.py').read_text(encoding='utf-8')
 assert 'stabilize_html_images(' in source
 assert 'permanent image hard gate failed' in source
 assert source.index('stabilize_html_images(') < source.index('requests.post(endpoint')
