from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from manuscript_text_contract import active_tex, cited_url, has_concepts, has_label


class ManuscriptTextContractTests(unittest.TestCase):
    def test_comments_cannot_satisfy_a_scientific_or_label_check(self) -> None:
        text = 'Active forecast discussion. % CRPS\n% \\label{sec:data}'
        self.assertFalse(has_concepts(text, 'CRPS'))
        self.assertFalse(has_label(text, 'sec:data'))
        self.assertIn(r'95\% predictive', active_tex(r'95\% predictive % stale'))

    def test_repository_url_must_be_direct_or_in_a_cited_entry(self) -> None:
        url = 'https://example.org/software'
        bib = '@misc{used,\nurl={' + url + '}\n}\n@misc{unused,\nurl={https://example.org/unused}\n}'
        self.assertTrue(cited_url(r'Workflow \citep{used}.', bib, url))
        self.assertFalse(cited_url('% \\citep{used}', bib, url))
        self.assertFalse(cited_url(r'Workflow \citep{unused}.', bib, url))


if __name__ == '__main__':
    unittest.main()
