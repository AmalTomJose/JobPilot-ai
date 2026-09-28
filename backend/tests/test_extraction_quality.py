"""Realistic synthetic layouts and adversarial cases for extraction v2."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import pymupdf
from app.services.pdf_service import PDFService
from app.services.resume_parser import parse_resume
from app.services.job_parser import parse_job_email
from app.middlewares.exception_middleware import UserException


class ResumeQualityTests(unittest.TestCase):
    def test_common_unlabeled_header_and_inline_sections(self):
        raw = """ALEX MORGAN
alex@example.com | +91 98765 43210 | https://github.com/alex
Career Objective: Build reliable systems.
Technical Skills: Python, SQL, C++, CI/CD
Work History
Backend Developer at Example Labs | Jan. 2023 – Present
• Built APIs with FastAPI and
  PostgreSQL for internal reporting.
Education
B.Tech Computer Science | Example University | 2019 to 2023
Projects
Job Tracker
Tech stack: Python, FastAPI
- Tracks applications.
"""
        draft = parse_resume(raw).draft
        self.assertEqual(draft.contact.name, 'ALEX MORGAN')
        self.assertEqual(draft.contact.phone, '+91 98765 43210')
        self.assertEqual(draft.skills, ['Python', 'SQL', 'C++', 'CI/CD'])
        self.assertEqual(draft.experience[0].company, 'Example Labs')
        self.assertEqual(draft.experience[0].date_text, 'Jan. 2023 – Present')
        self.assertEqual(draft.experience[0].description, ['Built APIs with FastAPI and PostgreSQL for internal reporting.'])
        self.assertEqual(draft.education[0].institution, 'Example University')
        self.assertEqual(draft.education[0].date_text, '2019 to 2023')
        self.assertEqual(draft.projects[0].name, 'Job Tracker')
        self.assertEqual(draft.projects[0].technologies, ['Python', 'FastAPI'])

    def test_company_first_entries_without_blank_separators(self):
        draft = parse_resume('EXPERIENCE\nExample Labs\nBackend Developer\nJan 2023 - Present\n- Built APIs.\nSample Systems\nData Analyst\n2021 - 2022\n- Built reports.').draft
        self.assertEqual([(row.company, row.title) for row in draft.experience], [('Example Labs', 'Backend Developer'), ('Sample Systems', 'Data Analyst')])

    def test_blank_lines_inside_header_do_not_split_entry(self):
        draft = parse_resume('EXPERIENCE\nBackend Developer\n\nExample Labs\n\n2023 - Present\n\n- Built APIs.').draft
        self.assertEqual(len(draft.experience), 1)
        self.assertEqual(draft.experience[0].company, 'Example Labs')

    def test_company_first_inline_date_stays_with_role(self):
        draft = parse_resume('EXPERIENCE\nExample Labs | Jan 2023 - Present\nBackend Developer\n- Built APIs.').draft
        self.assertEqual(len(draft.experience), 1)
        self.assertEqual(draft.experience[0].company, 'Example Labs')
        self.assertEqual(draft.experience[0].title, 'Backend Developer')

    def test_missing_company_does_not_use_achievement_as_employer(self):
        draft = parse_resume('EXPERIENCE\nEngineer | 2023 - Present\nBuilt APIs.').draft
        self.assertIsNone(draft.experience[0].company)

    def test_layout_uncertainty_does_not_erase_other_sections(self):
        draft = parse_resume('SKILLS\nPython, SQL\nEXPERIENCE\nEngineer      Another Company\n2023 - Present\nEDUCATION\nBSc Computer Science\nExample University\n2020').draft
        self.assertEqual(draft.skills, ['Python', 'SQL'])
        self.assertIsNone(draft.experience[0].company)
        self.assertEqual(draft.education[0].institution, 'Example University')

    def test_skill_categories_unicode_and_project_scope(self):
        draft = parse_resume('SKILLS\nProgramming languages: Python, C++\nCloud platforms: AWS, Azure\nPROJECTS\nProject: Tracker\nTechnologies: FastAPI, PostgreSQL\n- Track jobs.').draft
        self.assertEqual(draft.skills, ['Python', 'C++', 'AWS', 'Azure'])
        self.assertEqual(draft.projects[0].technologies, ['FastAPI', 'PostgreSQL'])
        self.assertEqual(parse_resume('ＳＫＩＬＬＳ： Python, SQL').draft.skills, ['Python', 'SQL'])

    def test_university_first_and_consecutive_labeled_entries(self):
        draft = parse_resume('EDUCATION\nExample University\nBSc Computer Science\n2019 - 2023\nEXPERIENCE\nTitle: Engineer\nCompany: One\nDates: 2023 - Present\nTitle: Analyst\nCompany: Two\nDates: 2021 - 2022').draft
        self.assertEqual(draft.education[0].institution, 'Example University')
        self.assertEqual([entry.company for entry in draft.experience], ['One', 'Two'])

    def test_dates_and_numeric_urls_are_not_contact_phone(self):
        draft = parse_resume('Alex Morgan\nalex@example.com\nhttps://example.com/12345678901\n01/2020 - 12/2024\nSKILLS\nPython').draft
        self.assertIsNone(draft.contact.phone)

    def test_ambiguous_phone_and_arbitrary_sentence_name_stay_empty(self):
        draft = parse_resume('Looking for opportunities\na@example.com\n+1 415 555 0123 | +1 415 555 0456').draft
        self.assertIsNone(draft.contact.name)
        self.assertIsNone(draft.contact.phone)

    def test_exported_symbol_bullets_and_associate_roles(self):
        source = """Professional Experience
Software Developer Associate | Example Health | Mar 2026 - Present
\uf0b7Develop APIs with validation and
reusable business logic.
\uf0b7Write tests and contribute to
planning.
Infra Managed Service Associate | Example Operations | Aug 2023 - Jun 2024
\uf0b7Monitor infrastructure and keep
operations documented.
Software Developer Intern | Example Digital | Aug 2022 - Jan 2023
\uf0b7Develop an online platform and
contribute to testing.
Projects
Catering App | Full Stack Online Catering Platform
\uf0b7Built a web application with carts,
orders, and checkout.
\uf0b7Integrated payments and deployed
with HTTPS.
Education and Training
Web Development Training | Example Academy | Jul 2024 - Feb 2026
Completed practical coursework.
Bachelor of Computer Applications | 2019 - 2022
Example College of Applied Sciences
"""
        draft = parse_resume(source).draft
        self.assertEqual([e.company for e in draft.experience], ['Example Health', 'Example Operations', 'Example Digital'])
        self.assertEqual([len(e.description) for e in draft.experience], [2, 1, 1])
        self.assertEqual(draft.experience[0].description[0], 'Develop APIs with validation and reusable business logic.')
        self.assertEqual(draft.experience[1].description, ['Monitor infrastructure and keep operations documented.'])
        self.assertEqual(len(draft.projects), 1)
        self.assertEqual(draft.projects[0].name, 'Catering App')
        self.assertEqual(draft.projects[0].description, ['Built a web application with carts, orders, and checkout.', 'Integrated payments and deployed with HTTPS.'])
        self.assertEqual([e.institution for e in draft.education], ['Example Academy', 'Example College of Applied Sciences'])
        self.assertNotIn('Education', draft.projects[0].source_text)

    def test_long_explicit_skill_lists_keep_full_names(self):
        draft = parse_resume('Technical Skills\nBackend and Databases: FastAPI, Node.js, Express.js, REST APIs, SQL Server, MySQL, MongoDB\nFrontend: React, Next.js, Tailwind CSS, TanStack Query, Zustand, React Hook Form, Zod\nCloud and Tools: AWS EC2, AWS S3, Docker, Nginx, PM2, Git, GitHub, Postman, Pytest').draft
        for skill in ('Express.js', 'REST APIs', 'SQL Server', 'Tailwind CSS', 'React Hook Form', 'AWS EC2', 'AWS S3', 'PM2', 'Pytest'):
            self.assertIn(skill, draft.skills)
        self.assertNotIn('Backend and Databases: FastAPI', draft.skills)


class EmailQualityTests(unittest.TestCase):
    def test_realistic_alert_subject_multiline_fields_and_apply_button(self):
        source = """Subject: Job alert: Backend Developer at Example Labs
Hi Alex,
Location:
Bengaluru (Hybrid)
Full-time
About the role
Build APIs with Python and FastAPI.
Requirements
Experience with PostgreSQL and Docker.
[Apply now](https://example.com/jobs/123)
Unsubscribe: https://example.com/preferences
"""
        result = parse_job_email(source)
        draft = result.draft_data
        self.assertEqual((draft.title, draft.company), ('Backend Developer', 'Example Labs'))
        self.assertEqual(draft.location, 'Bengaluru (Hybrid)')
        self.assertEqual(draft.work_mode, 'hybrid')
        self.assertEqual(draft.employment_type, 'Full-time')
        self.assertEqual(draft.skills, ['Python', 'FastAPI', 'PostgreSQL', 'Docker'])
        self.assertEqual(draft.application_url, 'https://example.com/jobs/123')
        self.assertNotIn('Unsubscribe', draft.description)

    def test_hiring_headline_and_multiline_labels(self):
        draft = parse_job_email('Example Labs is hiring a Backend Developer!\nWorkplace type: Remote\nKey skills:\n- Python\n- SQL\nApply now:\nhttps://example.com/1').draft_data
        self.assertEqual(draft.title, 'Backend Developer')
        self.assertEqual(draft.company, 'Example Labs')
        self.assertEqual(draft.skills, ['Python', 'SQL'])
        self.assertEqual(draft.application_url, 'https://example.com/1')

    def test_multiple_unlabeled_jobs_do_not_mix(self):
        result = parse_job_email('Backend Developer at One Labs\nDesigner at Two Labs\nApply: https://example.com/1')
        self.assertIsNone(result.draft_data.title)
        self.assertIsNone(result.draft_data.company)
        self.assertIn('MULTIPLE_JOBS', [warning.code for warning in result.warnings])

    def test_conflicting_modes_and_negated_skills_are_not_guessed(self):
        draft = parse_job_email('Work mode: Remote or hybrid\nRequirements:\nPython is required.\nJava is not required.\nNo SQL experience needed.').draft_data
        self.assertIsNone(draft.work_mode)
        self.assertEqual(draft.skills, ['Python'])

    def test_markdown_bullets_and_fullwidth_colon(self):
        draft = parse_job_email('**Job title:** Developer\n• Company： Example Labs\nSkills: C++, C#, CI/CD, Node.js\nApply here: Visit https://example.com/1').draft_data
        self.assertEqual(draft.title, 'Developer')
        self.assertEqual(draft.company, 'Example Labs')
        self.assertEqual(draft.skills, ['C++', 'C#', 'CI/CD', 'Node.js'])
        self.assertEqual(draft.application_url, 'https://example.com/1')

    def test_missing_scalar_does_not_swallow_next_heading(self):
        draft = parse_job_email('Company:\nLocation: London\nTitle: Engineer').draft_data
        self.assertIsNone(draft.company)
        self.assertEqual(draft.location, 'London')

    def test_prose_preserved_without_invented_fields(self):
        source = 'Hello Alex,\nWe need someone to help our team.\nPlease contact the recruiter.'
        draft = parse_job_email(source).draft_data
        self.assertEqual(draft.description, source)
        self.assertIsNone(draft.title)
        self.assertIsNone(draft.company)


class PDFQualityTests(unittest.TestCase):
    def extract(self, document):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.pdf'
            document.save(path)
            return PDFService.extract_text(str(path))

    def test_content_stream_order_does_not_control_reading_order(self):
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((50, 140), 'Python, SQL')
            page.insert_text((50, 50), 'Alex Morgan')
            page.insert_text((50, 120), 'SKILLS')
            text = self.extract(document)
        self.assertLess(text.index('Alex Morgan'), text.index('SKILLS'))
        self.assertEqual(parse_resume(text).draft.skills, ['Python', 'SQL'])

    def test_two_columns_are_read_separately(self):
        with pymupdf.open() as document:
            page = document.new_page(width=600, height=800)
            # Interleaved drawing order is common in exported two-column resumes.
            left = ['SKILLS', 'Python', 'SQL', 'EDUCATION', 'BSc Computer Science', 'Example University', '2020']
            right = ['EXPERIENCE', 'Backend Developer', 'Example Labs', '2023 - Present', '- Built APIs.', 'PROJECTS', 'Project: Tracker']
            for index, (a, b) in enumerate(zip(left, right)):
                page.insert_text((40, 100 + index * 22), a)
                page.insert_text((300, 100 + index * 22), b)
            text = self.extract(document)
        self.assertLess(text.index('Example University'), text.index('EXPERIENCE'))
        draft = parse_resume(text).draft
        self.assertEqual(draft.skills, ['Python', 'SQL'])
        self.assertEqual(draft.experience[0].company, 'Example Labs')

    def test_right_aligned_dates_stay_with_entry(self):
        with pymupdf.open() as document:
            page = document.new_page(width=600, height=800)
            for text, y in [('EXPERIENCE', 50), ('Backend Developer', 90), ('Example Labs', 110), ('- Built APIs.', 150)]:
                page.insert_text((40, y), text)
            page.insert_text((430, 110), '2023 - Present')
            extracted = self.extract(document)
        self.assertEqual(parse_resume(extracted).draft.experience[0].company, 'Example Labs')

    def test_mixed_image_only_page_does_not_silently_disappear(self):
        with pymupdf.open() as document:
            document.new_page().insert_text((50, 50), 'Selectable page')
            page = document.new_page()
            pixmap = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 10, 10), False)
            pixmap.clear_with(255)
            page.insert_image(pymupdf.Rect(50, 50, 100, 100), pixmap=pixmap)
            with self.assertRaises(UserException):
                self.extract(document)
