#!/usr/bin/env python3
"""
Minimal RFC parser with fallback for micro-issue generation.
- Primary: parse sections titled like `Game-RFC-XXX-N: Title`.
- Fallback: parse a "Micro tasks" checklist under a heading `### Micro tasks` with `- [ ]` items.
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class MicroIssueTemplate:
    title: str
    body: str

class RFCParser:
    def __init__(self, rfc_path: str):
        self.path = Path(rfc_path)
        self.text = self.path.read_text(encoding='utf-8')

    def _parse_micro_sections(self) -> List[MicroIssueTemplate]:
        templates: List[MicroIssueTemplate] = []
        # Match lines like: ## Game-RFC-003-1: Console loop skeleton
        pattern = re.compile(r'^##\s+(Game-RFC-\d{3}-\d+):\s*(.+)$', re.MULTILINE)
        for m in pattern.finditer(self.text):
            section_id = m.group(1)
            title = m.group(2).strip()
            templates.append(MicroIssueTemplate(
                title=f"{section_id}: {title}",
                body=f"@copilot Implement: {section_id}: {title}\n\nSee `{self.path.name}` for details."
            ))
        return templates

    def _parse_micro_checklist(self) -> List[MicroIssueTemplate]:
        templates: List[MicroIssueTemplate] = []
        # Find a '### Micro tasks' section and collect '- [ ] ' lines until next heading
        section_rx = re.compile(r'^###\s+Micro tasks\s*$', re.MULTILINE)
        m = section_rx.search(self.text)
        if not m:
            return templates
        start = m.end()
        tail = self.text[start:]
        end_match = re.search(r'^#{2,}.+$', tail, re.MULTILINE)
        block = tail[:end_match.start()] if end_match else tail
        for line in block.splitlines():
            line = line.strip()
            if line.startswith('- [ ]'):
                t = line.split('] ', 1)[1].strip()
                templates.append(MicroIssueTemplate(
                    title=t,
                    body=f"@copilot Please implement: {t}\n\nSource: `{self.path.name}`"
                ))
        return templates

    def generate(self) -> List[MicroIssueTemplate]:
        items = self._parse_micro_sections()
        if items:
            return items
        return self._parse_micro_checklist()


def parse_any_rfc(rfc_path: str, rfc_number: str):
    parser = RFCParser(rfc_path)
    return parser.generate()
