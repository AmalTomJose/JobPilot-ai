from pathlib import Path
import unittest
from app.services.resume_parser import parse_resume, MAX_TEXT_LENGTH, PARSER_VERSION

FIXTURES = Path(__file__).parent / 'fixtures' / 'resumes'


class ParserTests(unittest.TestCase):
    def test_standard_resume(self):
        result = parse_resume((FIXTURES / 'standard.txt').read_text())
        draft = result.draft
        self.assertEqual(draft.contact.name, 'Alex Morgan')
        self.assertEqual(draft.contact.email, 'alex@example.com')
        self.assertEqual(draft.contact.phone, '+1 (415) 555-0123')
        self.assertEqual(draft.contact.location, 'Seattle')
        self.assertEqual(draft.contact.links, ['https://github.com/alex'])
        self.assertEqual(draft.summary, 'Backend developer building APIs.')
        self.assertEqual(draft.skills, ['Python', 'FastAPI', 'PostgreSQL', 'C++', 'C#', 'Node.js', 'CI/CD'])
        self.assertEqual(len(draft.experience), 2)
        self.assertEqual(draft.experience[0].company, 'Example Company')
        self.assertEqual(draft.experience[0].date_text, '2023 - Present')
        self.assertEqual(draft.experience[0].description, ['Built REST APIs.', 'Improved response times.'])
        self.assertEqual(draft.experience[1].title, 'Data Analyst')
        self.assertEqual(draft.education[0].degree, 'BSc Computer Science')
        self.assertIsNone(draft.education[0].field_of_study)
        self.assertEqual(draft.projects[0].name, 'Resume Explorer')
        self.assertEqual(draft.projects[0].technologies, ['Python', 'FastAPI'])
        self.assertIn('Example Certificate', draft.unclassified_text)
        self.assertEqual(result.parser_version, PARSER_VERSION)

    def test_ambiguous_fields_stay_empty_and_source_is_preserved(self):
        result = parse_resume((FIXTURES / 'ambiguous.txt').read_text())
        self.assertIsNone(result.draft.contact.name)
        self.assertIsNone(result.draft.contact.email)
        self.assertIsNone(result.draft.experience[0].company)
        self.assertIsNone(result.draft.experience[0].title)
        self.assertIn('Summer 2023', result.draft.experience[0].source_text)
        self.assertIsNone(result.draft.education[0].institution)
        self.assertIsNone(result.draft.projects[0].name)
        codes = {w.code for w in result.warnings}
        self.assertTrue({'CONTACT_NAME_UNCERTAIN', 'AMBIGUOUS_EMAIL', 'AMBIGUOUS_EXPERIENCE', 'AMBIGUOUS_EDUCATION', 'AMBIGUOUS_PROJECT'} <= codes)

    def test_column_text_does_not_become_invented_employers_or_skills(self):
        result = parse_resume((FIXTURES / 'columns.txt').read_text())
        self.assertIn('POSSIBLE_LAYOUT_ISSUE', [w.code for w in result.warnings])
        self.assertIsNone(result.draft.experience[0].company)
        self.assertEqual(result.draft.skills, [])

    def test_aliases_case_colons_and_line_endings(self):
        draft = parse_resume('Name: Alex Morgan\r\nprofile:\r\nHello\r\n\r\ncore competencies:\r\n• Python\r\n• SQL\r\nacademic background:\r\nDegree: MSc\r\nInstitution: Example School').draft
        self.assertEqual(draft.summary, 'Hello')
        self.assertEqual(draft.skills, ['Python', 'SQL'])
        self.assertEqual(draft.education[0].institution, 'Example School')

    def test_no_headings_preserves_text_and_missing_values(self):
        result = parse_resume('An unstructured resume without supported headings.')
        self.assertIsNone(result.draft.contact.email)
        self.assertEqual(result.draft.skills, [])
        self.assertEqual(result.draft.experience, [])
        self.assertIn('NO_SECTIONS_FOUND', [w.code for w in result.warnings])
        self.assertEqual(result.draft.unclassified_text, 'An unstructured resume without supported headings.')

    def test_heading_word_inside_sentence_does_not_start_section(self):
        result = parse_resume('SUMMARY\nMy experience includes Python.\nSKILLS\nPython')
        self.assertEqual(result.draft.summary, 'My experience includes Python.')
        self.assertEqual(result.draft.experience, [])

    def test_dates_are_not_phone_numbers(self):
        self.assertIsNone(parse_resume('2020 - 2024\nName: Alex Morgan').draft.contact.phone)

    def test_repeated_sections_keep_both_blocks(self):
        draft = parse_resume('SKILLS\nPython\nSKILLS:\nPython, C++').draft
        self.assertEqual(draft.skills, ['Python', 'C++'])

    def test_explicit_fields_preserve_unusual_dates(self):
        draft = parse_resume('EXPERIENCE\nTitle: Engineer\nCompany: Example\nDates: Summer 2023\nLocation: Remote').draft
        self.assertEqual(draft.experience[0].date_text, 'Summer 2023')
        self.assertEqual(draft.experience[0].location, 'Remote')

    def test_empty_and_excessive_input_rejected(self):
        for text in ['', ' \n ', 'x' * (MAX_TEXT_LENGTH + 1)]:
            with self.subTest(length=len(text)), self.assertRaises(ValueError):
                parse_resume(text)

    def test_deterministic_and_no_shared_mutable_defaults(self):
        first = parse_resume('SKILLS\nPython')
        self.assertEqual(first, parse_resume('SKILLS\nPython'))
        first.draft.skills.append('mutated')
        self.assertEqual(parse_resume('SKILLS\nPython').draft.skills, ['Python'])


    def test_blank_line_before_bullets_does_not_create_an_extra_job(self):
        result = parse_resume('EXPERIENCE\nEngineer\nExample Company\n2023 - Present\n\n- Built APIs.')
        self.assertEqual(len(result.draft.experience), 1)
        self.assertEqual(result.draft.experience[0].description, ['Built APIs.'])

    def test_plain_description_after_recognized_header_is_preserved(self):
        entry = parse_resume('EXPERIENCE\nEngineer\nExample Company\n2023 - Present\nBuilt REST APIs.').draft.experience[0]
        self.assertEqual(entry.description, ['Built REST APIs.'])


    def test_date_is_not_misclassified_as_an_employer(self):
        entry = parse_resume('EXPERIENCE\nEngineer | 2023 - Present').draft.experience[0]
        self.assertIsNone(entry.company)
