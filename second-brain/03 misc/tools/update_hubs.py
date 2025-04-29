#!/usr/bin/env python3

import re
import yaml
from datetime import date
from pathlib import Path

# Base paths (adjusted for location in tools/)
ROOT_DIR = Path(__file__).resolve().parents[3]
NOTES_DIR = ROOT_DIR / '01 notes'
HUBS_DIR = ROOT_DIR / '00 hubs'
TEMPLATE_PATH = ROOT_DIR / '03 misc' / 'templates' / 'hub.md'

# Markers
LINKS_START = '<!-- LINKS_START -->'
LINKS_END = '<!-- LINKS_END -->'

def normalize(name):
    return name.lower().replace('-', ' ').replace('_', ' ').strip()

def extract_yaml_frontmatter(file_path):
    """Extract YAML frontmatter from a markdown file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines or not lines[0].strip() == '---':
        return None

    yaml_lines = []
    for line in lines[1:]:
        if line.strip() == '---':
            break
        yaml_lines.append(line)

    try:
        return yaml.safe_load(''.join(yaml_lines))
    except yaml.YAMLError as e:
        print(f"[Error] Failed parsing YAML in {file_path.name}: {e}")
        return None

def collect_links():
    """Collect hub-to-note relationships from note frontmatter."""
    hub_links = {}

    for note_file in NOTES_DIR.glob('*.md'):
        yaml_data = extract_yaml_frontmatter(note_file)
        if not yaml_data:
            print(f"[Warning] Skipping {note_file.name}: No YAML.")
            continue

        note_title = yaml_data.get('title')
        linked_hubs = yaml_data.get('linked_hubs', [])

        if not note_title:
            print(f"[Warning] Skipping {note_file.name}: No title.")
            continue

        for raw in linked_hubs:
            if isinstance(raw, str):
                raw = raw.strip()
                if raw.startswith('[[') and raw.endswith(']]'):
                    clean_path = raw[2:-2].strip()
                else:
                    print(f"[Warning] Hub path not in [[...]] format: '{raw}' in {note_file.name}")
                    clean_path = raw
                hub_links.setdefault(clean_path, []).append(note_title)

    return hub_links

def create_hub_file(category, raw_name):
    """Create a new hub file using the standard template."""
    file_path = HUBS_DIR / category / f"{raw_name}.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if not TEMPLATE_PATH.exists():
        print(f"[Error] Missing hub template: {TEMPLATE_PATH}")
        return None

    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()

    today = date.today().isoformat()
    hub_title = raw_name.title()

    filled = template \
        .replace("{{hub_title}}", hub_title) \
        .replace("{{core / parent / topic}}", category) \
        .replace("{{YYYY-MM-DD}}", today)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(filled)

    print(f"[Created] New hub: {file_path.relative_to(ROOT_DIR)}")
    return file_path

def find_hub_file(hub_path):
    """Find or create a hub file by normalized name."""
    try:
        category, raw_name = hub_path.split('/', 1)
    except ValueError:
        print(f"[Error] Invalid hub path format: '{hub_path}'")
        return None

    category_path = HUBS_DIR / category
    if not category_path.exists():
        print(f"[Warning] Missing hub folder: {category_path}")
        return None

    target = normalize(raw_name)
    for hub_file in category_path.glob('*.md'):
        if normalize(hub_file.stem) == target:
            return hub_file

    return create_hub_file(category, raw_name)

def update_hub_file(hub_path, linked_notes):
    """Insert or update linked notes section in the hub."""
    with open(hub_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = re.compile(f'{LINKS_START}(.*?){LINKS_END}', re.DOTALL)
    notes_block = '\n'.join(f"- [[{note}]]" for note in sorted(linked_notes))
    new_section = f"{LINKS_START}\n{notes_block}\n{LINKS_END}"

    if pattern.search(content):
        updated = pattern.sub(new_section, content)
    else:
        updated = content.strip() + f"\n\n## 🔗 Linked Notes\n{new_section}"

    with open(hub_path, 'w', encoding='utf-8') as f:
        f.write(updated)

def main():
    print("[INFO] Starting Hubkasten hub update...")
    hub_links = collect_links()

    if not hub_links:
        print("[INFO] No linked hubs found. Exiting.")
        return

    updated = 0

    for hub_path, notes in hub_links.items():
        hub_file = find_hub_file(hub_path)
        if hub_file:
            update_hub_file(hub_file, notes)
            print(f"[OK] Updated: {hub_file.relative_to(ROOT_DIR)}")
            updated += 1
        else:
            print(f"[Error] Could not create/find hub: {hub_path}")

    print(f"[DONE] {updated} hubs updated.")

if __name__ == "__main__":
    main()

