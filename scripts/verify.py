#!/usr/bin/env python3
"""Build both deployment forms and verify migrated content and internal resources."""
import hashlib, json, os, re, shutil, subprocess, tempfile, urllib.parse
from html.parser import HTMLParser
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []; self.canonical = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('a','link') and a.get('href'): self.links.append(a['href'])
        if tag in ('img','script') and a.get('src'): self.links.append(a['src'])
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical = a.get('href')

def verify():
    manifest = json.loads((ROOT/'migration/manifest.json').read_text())
    assert len(manifest['contents']) == 26
    assert len({r['url'] for r in manifest['contents']}) == 26
    assert len(manifest['assets']) == 5
    for item in manifest['assets']:
        data = (ROOT/'static'/item['path'].lstrip('/')).read_bytes()
        assert len(data) == item['bytes']
        assert hashlib.sha256(data).hexdigest() == item['sha256']
    for item in manifest['contents']:
        raw = (ROOT/item['file']).read_text()
        meta, _ = json.JSONDecoder().raw_decode(raw)
        assert meta['url'] == item['url'] and meta['typecho_id'] == item['id']
        assert not any(key in meta for key in ('password','authCode','mail'))
    hugo = os.environ.get('HUGO_BINARY', 'hugo')
    for base in ('https://yangmame.github.io/YangMame/', 'https://blog.yangmame.org/'):
        with tempfile.TemporaryDirectory(prefix='hugo-check-') as directory:
            subprocess.run([hugo,'--baseURL',base,'--destination',directory,'--panicOnWarning'],cwd=ROOT,check=True)
            output = Path(directory); origin = urllib.parse.urlsplit(base)
            for item in manifest['contents']:
                path = output/item['url'].lstrip('/')
                assert path.is_file(), f'Missing old URL {path}'
                parser = Page(); parser.feed(path.read_text())
                assert urllib.parse.unquote(parser.canonical) == base + item['url'].lstrip('/')
            for path in output.rglob('*.html'):
                text = path.read_text()
                assert '{{<' not in text and 'ZgotmplZ' not in text, path
                parser = Page(); parser.feed(text)
                current = base + str(path.relative_to(output))
                for link in parser.links:
                    target = urllib.parse.urlsplit(urllib.parse.urljoin(current,link))
                    if target.netloc != origin.netloc or target.scheme not in ('http','https'): continue
                    decoded = urllib.parse.unquote(target.path)
                    assert decoded.startswith(origin.path), f'Escaped base path: {link} in {path}'
                    local = output/decoded[len(origin.path):]
                    if target.path.endswith('/'): local = local/'index.html'
                    assert local.is_file(), f'Broken internal link {link} in {path}'
            index = json.loads((output/'index.json').read_text())
            assert len(index) == 25
            assert all(item['url'].startswith(origin.path) for item in index)
            assert any('EAPI' in item['content'] for item in index)
            assert (output/'index.xml').is_file() and (output/'sitemap.xml').is_file()
            for asset in manifest['assets']:
                assert (output/asset['path'].lstrip('/')).read_bytes() == (ROOT/'static'/asset['path'].lstrip('/')).read_bytes()
            print('Verified 26 URLs, 5 assets, search index and all local links:',base)
    print('All migration checks passed.')
if __name__ == '__main__': verify()
