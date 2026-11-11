"""Dependency-free local link/anchor/fence checks for the launch documentation.

This is not a Markdown style linter or Mermaid renderer; those limits are explicit.
"""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]


def slug(value):
    value = re.sub(r'<[^>]*>', '', value).strip().lower().replace('`', '')
    value = re.sub(r'[^\w\- ]', '', value, flags=re.UNICODE)
    return value.replace(' ', '-')


def check():
    files = [ROOT / 'README.md', *sorted((ROOT / 'docs/milestone6').rglob('*.md'))]
    errors = []
    links = 0
    mermaid = 0
    for path in files:
        text = path.read_text(encoding='utf-8')
        fences = re.findall(r'^```.*$', text, flags=re.M)
        if len(fences) % 2:
            errors.append(f'{path.relative_to(ROOT)}: unbalanced code fences')
        for diagram in re.findall(r'```mermaid\n(.*?)\n```', text, flags=re.S):
            mermaid += 1
            if not diagram.startswith('flowchart '):
                errors.append(f'{path.relative_to(ROOT)}: unsupported diagram header')
            if len(re.findall(r'^\s*subgraph\b', diagram, flags=re.M)) != len(re.findall(r'^\s*end\s*$', diagram, flags=re.M)):
                errors.append(f'{path.relative_to(ROOT)}: unbalanced Mermaid subgraph')
        for target in re.findall(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', text):
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith('//'):
                continue
            links += 1
            destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not destination.is_relative_to(ROOT) or not destination.is_file():
                errors.append(f'{path.relative_to(ROOT)}: missing/nonlocal target {target}')
                continue
            if parsed.fragment and destination.suffix == '.md':
                headings = re.findall(r'^#{1,6}\s+(.+?)\s*$', destination.read_text(encoding='utf-8'), flags=re.M)
                if unquote(parsed.fragment) not in {slug(value) for value in headings}:
                    errors.append(f'{path.relative_to(ROOT)}: missing anchor {target}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'{len(files)} Markdown files; {links} local links/anchors; fences balanced; {mermaid} basic Mermaid structure checks passed.')
    print('External URLs were not crawled. Mermaid rendering/style linting were not performed.')


if __name__ == '__main__':
    check()
