"""Read-only comparison of the committed shell, built distribution and public Pages shell."""
from pathlib import Path
import hashlib
import json
import os
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://nikoju1977.github.io/medicalvisionproai/index.html'
LIMIT = 5 * 1024 * 1024

def digest(data):
    return hashlib.sha256(data).hexdigest()

def compare(source, built, served):
    return {
        'source_sha256': digest(source),
        'dist_sha256': digest(built),
        'source_equals_dist': source == built,
        'public_sha256': digest(served) if served is not None else None,
        'public_matches_source': served == source if served is not None else None,
        'public_matches_dist': served == built if served is not None else None,
    }

def main():
    source = (ROOT / 'index.html').read_bytes()
    built = (ROOT / 'dist/index.html').read_bytes()
    served = None
    status = None
    failure = None
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'Studio-Niko-Publication-Audit', 'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity'})
        with urllib.request.urlopen(req, timeout=20) as response:
            status = response.status
            if response.geturl() != URL or status != 200:
                raise ValueError('Unexpected public URL or response')
            data = response.read(LIMIT + 1)
            if len(data) > LIMIT:
                raise ValueError('Public shell exceeds comparison limit')
            served = data
    except Exception as error:
        failure = type(error).__name__
    config = {}
    try:
        config = json.loads(os.environ.get('PAGES_CONFIG', '{}'))
        if not isinstance(config, dict):
            config = {}
    except ValueError:
        pass
    result = compare(source, built, served)
    src = config.get('source') or {}
    result.update({
        'checked_commit': os.environ.get('GITHUB_SHA'),
        'build_type': config.get('build_type'),
        'branch': src.get('branch'),
        'path': src.get('path'),
        'http_status': status,
        'public_fetch_error': failure,
        'clinical_validation': False,
        'production_revision_proven': False,
    })
    print('PAGES_DISTRIBUTION ' + json.dumps(result, sort_keys=True))
    (ROOT / 'pages-distribution-proof.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
