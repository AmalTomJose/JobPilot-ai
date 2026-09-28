import unittest
from pathlib import Path
from app.services.job_parser import parse_job_email, canonical_url


class JobParserTests(unittest.TestCase):
    def test_labeled_email_and_source_unchanged(self):
        source = (Path(__file__).parent / 'fixtures/jobs/labeled.txt').read_text()
        result = parse_job_email(source)
        self.assertEqual(result.draft_data.title, 'Backend Developer')
        self.assertEqual(result.draft_data.company, 'Example Labs')
        self.assertEqual(result.draft_data.work_mode, 'hybrid')
        self.assertEqual(result.draft_data.skills, ['Python', 'SQL', 'FastAPI'])
        self.assertIn('Write tests', result.draft_data.description)
        self.assertIn('Requirements:', result.draft_data.description)
        self.assertIn('utm_source=email', result.draft_data.application_url)
        self.assertEqual(result.parser_version, 'job-rules-v3')
        self.assertEqual(source, (Path(__file__).parent / 'fixtures/jobs/labeled.txt').read_text())

    def test_unlabeled_prose_is_not_invented(self):
        result = parse_job_email('We need a brilliant engineer in London. Contact our recruiter.')
        self.assertIsNone(result.draft_data.title)
        self.assertIsNone(result.draft_data.company)
        self.assertIsNone(result.draft_data.location)
        self.assertEqual(result.draft_data.description, 'We need a brilliant engineer in London. Contact our recruiter.')

    def test_multiple_jobs_do_not_mix_fields(self):
        result = parse_job_email('Title: Engineer\nCompany: One\nTitle: Designer\nCompany: Two\nApply: https://example.com')
        self.assertIsNone(result.draft_data.title)
        self.assertIsNone(result.draft_data.application_url)
        self.assertIn('MULTIPLE_JOBS', [w.code for w in result.warnings])

    def test_multiple_links_stay_unknown(self):
        result = parse_job_email('https://example.com/jobs/1\nhttps://example.com/unsubscribe')
        self.assertIsNone(result.draft_data.application_url)
        self.assertIn('AMBIGUOUS_LINK', [w.code for w in result.warnings])

    def test_explicit_apply_link_takes_precedence(self):
        result = parse_job_email('Apply: https://example.com/jobs/1\nUnsubscribe: https://example.com/unsubscribe')
        self.assertEqual(result.draft_data.application_url, 'https://example.com/jobs/1')

    def test_single_unlabeled_link_requires_check(self):
        result = parse_job_email('See https://example.com/jobs/1.')
        self.assertEqual(result.draft_data.application_url, 'https://example.com/jobs/1')
        self.assertIn('CHECK_LINK', [w.code for w in result.warnings])

    def test_invalid_link_and_unknown_mode(self):
        result = parse_job_email('Apply: javascript:alert(1)\nWork mode: Flexible')
        self.assertIsNone(result.draft_data.application_url)
        self.assertIsNone(result.draft_data.work_mode)

    def test_repeated_fields_are_conservative_and_aliases_work(self):
        result = parse_job_email('ROLE: Developer\r\nEmployer: One\r\nEmployer: Two\r\nWork arrangement: On-site\r\nRequired skills: C++, C#, Node.js, c++')
        self.assertEqual(result.draft_data.title, 'Developer')
        self.assertIsNone(result.draft_data.company)
        self.assertEqual(result.draft_data.work_mode, 'onsite')
        self.assertEqual(result.draft_data.skills, ['C++', 'C#', 'Node.js'])

    def test_empty_and_oversized_input(self):
        for value in (' ', 'x'*100001):
            with self.assertRaises(ValueError): parse_job_email(value)

    def test_url_normalization_removes_only_known_tracking(self):
        self.assertEqual(canonical_url('https://EXAMPLE.com:443/jobs?id=1&utm_source=x#apply'), 'https://example.com/jobs?id=1')
        self.assertNotEqual(canonical_url('https://example.com/jobs?id=1'), canonical_url('https://example.com/jobs?id=2'))
        self.assertNotEqual(canonical_url('https://example.com/Jobs/1'), canonical_url('https://example.com/jobs/1'))
        self.assertNotEqual(canonical_url('http://example.com/jobs/1'), canonical_url('https://example.com/jobs/1'))
        self.assertEqual(canonical_url('https://example.com/jobs?b=2&a=1&gclid=x'), 'https://example.com/jobs?a=1&b=2')

    def test_hash_routes_and_repeated_query_values_keep_job_identity(self):
        self.assertNotEqual(canonical_url('https://example.com/#/jobs/1'), canonical_url('https://example.com/#/jobs/2'))
        self.assertNotEqual(canonical_url('https://example.com/jobs?id=1&id=2'), canonical_url('https://example.com/jobs?id=2&id=1'))
