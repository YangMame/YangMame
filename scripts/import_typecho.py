#!/usr/bin/env python3
"""Import Typecho 0001 backups without exporting account or comment records."""
import argparse, collections, datetime, gzip, hashlib, json, re, struct, urllib.parse, urllib.request
from pathlib import Path

MAGIC = b'%TYPECHO_BACKUP_0001%'
ROOT = Path(__file__).resolve().parents[1]

def parse_backup(path):
    data = Path(path).read_bytes()
    if not (data.startswith(MAGIC) and data.endswith(MAGIC)):
        raise ValueError('Invalid backup envelope')
    pos, records = len(MAGIC), []
    while pos < len(data) - len(MAGIC):
        start = pos
        table, schema_len, body_len = struct.unpack_from('<HHI', data, pos)
        pos += 8
        schema = json.loads(data[pos:pos + schema_len]); pos += schema_len
        body = data[pos:pos + body_len]; pos += body_len
        if hashlib.md5(data[start:pos]).hexdigest().encode() != data[pos:pos + 32]:
            raise ValueError(f'Checksum mismatch at {start}')
        pos += 32
        record, offset = {}, 0
        for key, length in schema.items():
            record[key] = None if length is None else body[offset:offset + length].decode('utf-8')
            offset += length or 0
        if offset != body_len:
            raise ValueError('Field length mismatch')
        records.append(record)
    if pos != len(data) - len(MAGIC):
        raise ValueError('Trailing data')
    return records

def original_url(url):
    return re.sub(r'^https?://web\.archive\.org/web/[^/]+/(https?://)', r'\1', url)

def timestamp(value):
    return datetime.datetime.fromtimestamp(int(value), datetime.timezone(datetime.timedelta(hours=8))).isoformat()

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
    if data.startswith(b'\x1f\x8b'):
        data = gzip.decompress(data)
    return data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('backup')
    args = parser.parse_args()
    records = parse_backup(args.backup)
    contents = [r for r in records if r.get('type') in ('post', 'page') and r.get('status') == 'publish' and not r.get('password')]
    known = {'/' + r['slug'] + '.html' for r in contents}
    manifest = {'contents': [], 'assets': [], 'notes': ['No category relationships or comments in supplied backup.']}
    assets = {}
    for row in contents:
        for url in re.findall(r'https?://[^\s<>\)\]"\x27]+', row['text'] or ''):
            original = urllib.parse.urlsplit(original_url(url))
            if original.hostname == 'blog.yangmame.org' and original.path.startswith('/usr/uploads/'):
                assets[original.path] = url
    for path, archive in sorted(assets.items()):
        target = ROOT / 'static' / path.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        source = archive
        if not target.exists():
            try:
                source = 'https://blog.yangmame.org' + path
                data = fetch(source)
            except Exception:
                source = archive
                data = fetch(re.sub(r'(/web/\d+)(?:im_|id_)?/', r'\1id_/', archive))
            if path.endswith('.png') and not data.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError(f'Not a PNG: {path}')
            if path.endswith('.txt') and not data.startswith(b'#'):
                raise ValueError(f'Unexpected attachment: {path}')
            target.write_bytes(data)
        data = target.read_bytes()
        manifest['assets'].append({'path': path, 'source': source, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    for row in contents:
        body = row['text'] or ''
        markdown = body.startswith('<!--markdown-->')
        if markdown: body = body[len('<!--markdown-->'):]
        def rewrite(match):
            raw = match.group(0)
            url = urllib.parse.urlsplit(original_url(raw))
            path = urllib.parse.unquote(url.path)
            if url.hostname == 'blog.yangmame.org' and (path in known or path in assets or path == '/'):
                value = path.lstrip('/') + ('?' + url.query if url.query else '') + ('#' + url.fragment if url.fragment else '')
                return '{{< siteurl ' + json.dumps(value, ensure_ascii=False) + ' >}}'
            return raw
        # Only rewrite URLs in link/image attributes or Markdown destinations, never code examples.
        if markdown:
            body = re.sub(r'(?<=\()https?://[^\s)]+', rewrite, body)
        else:
            body = re.sub(r'((?:href|src)=["\x27])(https?://[^"\x27]+)', lambda m: m[1] + rewrite(re.match(r'.*', m[2])), body)
        meta = {'title': row['title'], 'date': timestamp(row['created']), 'lastmod': timestamp(row['modified']), 'url': '/' + row['slug'] + '.html', 'type': 'posts' if row['type'] == 'post' else 'page', 'original_slug': row['slug'], 'typecho_id': int(row['cid'])}
        output = ROOT / 'content' / ('posts' if row['type'] == 'post' else 'pages') / (row['cid'] + ('.md' if markdown else '.html'))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n' + body + '\n', encoding='utf-8')
        manifest['contents'].append({'id': int(row['cid']), 'title': row['title'], 'url': meta['url'], 'file': str(output.relative_to(ROOT)), 'source_body_sha256': hashlib.sha256(row['text'].encode()).hexdigest()})
    (ROOT / 'migration/manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Imported {len(contents)} pages and {len(assets)} assets')

if __name__ == '__main__': main()
