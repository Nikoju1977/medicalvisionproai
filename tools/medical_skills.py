from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / 'skills'

NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
ALLOWED_STAGES = {'reading', 'comparison', 'quality', 'evidence', 'reporting'}

def _value(raw):
    raw = raw.strip()
    if not raw:
        return ''
    if raw[0] in '[{"' or raw in ('true', 'false', 'null') or re.fullmatch(r'-?\d+(?:\.\d+)?', raw):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return raw

def parse_skill(path):
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise ValueError(f'{path}: missing YAML front matter')
    end = text.find('\n---\n', 4)
    if end < 0:
        raise ValueError(f'{path}: unterminated YAML front matter')
    front = {}
    for lineno, line in enumerate(text[4:end].splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if ':' not in line:
            raise ValueError(f'{path}:{lineno}: invalid front matter line')
        key, raw = line.split(':', 1)
        key = key.strip()
        if key in front:
            raise ValueError(f'{path}:{lineno}: duplicate key {key}')
        front[key] = _value(raw)
    body = text[end + 5:].strip()

    name = front.get('name')
    description = front.get('description')
    metadata = front.get('metadata')
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ValueError(f'{path}: invalid skill name')
    if path.parent.name != name:
        raise ValueError(f'{path}: folder/name mismatch ({path.parent.name} != {name})')
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f'{path}: description is required')
    if len(description) > 1024:
        raise ValueError(f'{path}: description exceeds 1024 characters')
    if not isinstance(metadata, dict):
        raise ValueError(f'{path}: metadata must be a one-line JSON object')
    if metadata.get('human_review_required') is not True:
        raise ValueError(f'{path}: human_review_required must be true')
    if metadata.get('draft_only') is not True:
        raise ValueError(f'{path}: draft_only must be true')
    if metadata.get('stage') not in ALLOWED_STAGES:
        raise ValueError(f'{path}: invalid stage {metadata.get("stage")!r}')
    if not isinstance(metadata.get('purposes'), list) or not metadata['purposes']:
        raise ValueError(f'{path}: metadata.purposes must be a non-empty list')
    for key in ('agents', 'modalities', 'regions', 'tags'):
        if key in metadata and not isinstance(metadata[key], list):
            raise ValueError(f'{path}: metadata.{key} must be a list')
    if not body:
        raise ValueError(f'{path}: empty instructions')
    return {
        'name': name,
        'description': description.strip(),
        'metadata': metadata,
        'instructions': body,
        'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
    }

def load_catalog(skills_dir=SKILLS_DIR):
    if not skills_dir.is_dir():
        raise ValueError(f'missing skills directory: {skills_dir}')
    skills = [parse_skill(path) for path in sorted(skills_dir.glob('*/SKILL.md'))]
    if not skills:
        raise ValueError('no medical skills found')
    names = [skill['name'] for skill in skills]
    if len(names) != len(set(names)):
        raise ValueError('duplicate skill names')
    return skills

def manifest(skills=None):
    skills = skills if skills is not None else load_catalog()
    return {
        'schema_version': 1,
        'generated_from': 'skills/*/SKILL.md',
        'skill_count': len(skills),
        'safety': {
            'draft_only': True,
            'human_review_required': True,
            'skills_cannot_override_evidence_policy': True,
        },
        'skills': skills,
    }

def main():
    parser = argparse.ArgumentParser(description='Validate and compile MedicalVisionProAI SKILL.md files.')
    parser.add_argument('--check', action='store_true', help='validate only')
    parser.add_argument('--output', type=Path, help='write deterministic JSON manifest')
    args = parser.parse_args()

    data = manifest()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f"Medical skills OK: {data['skill_count']} validated skills")
    if not args.check and not args.output:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
