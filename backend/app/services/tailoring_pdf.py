"""Text-based A4 resume; escaped local content, no external resources."""
from html import escape
from io import BytesIO
import pymupdf


def render_resume(data, order):
    def text(value):
        return escape(str(value or ''))
    def line(values):
        return ' | '.join(text(value) for value in values if value)
    def bullets(items):
        return '<ul>' + ''.join('<li>' + text(item) + '</li>' for item in items) + '</ul>' if items else ''
    contact = data['contact']
    html = '<h1>' + text(contact.get('name')) + '</h1>'
    html += '<p class="contact">' + line([contact.get('email'),contact.get('phone'),contact.get('location')]) + '</p>'
    html += ''.join('<p class="contact">' + text(link) + '</p>' for link in contact.get('links', []))
    for section in order:
        value = data.get(section)
        if not value:
            continue
        html += '<h2>' + section.title() + '</h2>'
        if section == 'summary':
            html += '<p>' + text(value) + '</p>'
        elif section == 'skills':
            html += '<p>' + line(value) + '</p>'
        else:
            for entry in value:
                if section == 'experience':
                    html += '<h3>' + line([entry.get('title'),entry.get('company')]) + '</h3>'
                    html += '<p class="meta">' + line([entry.get('location'),entry.get('date_text')]) + '</p>'
                    html += bullets(entry.get('description', []))
                elif section == 'projects':
                    html += '<h3>' + text(entry.get('name')) + '</h3>'
                    html += bullets(entry.get('description', []))
                    if entry.get('technologies'):
                        html += '<p class="meta">' + line(entry['technologies']) + '</p>'
                    html += ''.join('<p class="meta">'+text(link)+'</p>' for link in entry.get('links', []))
                else:
                    html += '<h3>' + text(entry.get('institution')) + '</h3>'
                    html += '<p>' + line([entry.get('degree'),entry.get('field_of_study'),entry.get('date_text')]) + '</p>'
    css = '''body { font-family: sans-serif; font-size: 10.5pt; line-height: 1.35; color: #172c28; }
    h1 { font-size: 23pt; margin: 0 0 7pt; } h2 { font-size: 12pt; margin: 16pt 0 7pt; color: #17634f; border-bottom: 0.6pt solid #cbd8d2; padding-bottom: 4pt; page-break-after: avoid; }
    h3 { font-size: 10.5pt; margin: 9pt 0 3pt; page-break-after: avoid; }
    p { margin: 3pt 0 7pt; overflow-wrap: anywhere; } .contact { font-size: 9.5pt; margin: 2pt 0; }
    .meta { color: #445b54; font-size: 9.5pt; } ul { margin: 4pt 0 8pt; padding-left: 15pt; } li { margin-bottom: 4pt; }'''
    page_rect = pymupdf.paper_rect('a4')
    # Try progressively tighter spacing, keeping body text at least 9.5pt.
    for size, spacing, margin in [(10.5, 1.25, 36), (10, 1.18, 32), (9.5, 1.12, 30)]:
        compact = f"""body {{ font-size: {size}pt; line-height: {spacing}; }}
        h1 {{ font-size: 21pt; margin-bottom: 4pt; }}
        h2 {{ margin: 9pt 0 4pt; padding-bottom: 2pt; }}
        h3 {{ font-size: {size}pt; margin: 6pt 0 2pt; }}
        p {{ margin: 2pt 0 4pt; }} ul {{ margin: 2pt 0 4pt; }}
        li {{ margin-bottom: 2pt; }} .meta, .contact {{ font-size: 9.5pt; }}"""
        story = pymupdf.Story(html=html, user_css=css + compact)
        body_rect = pymupdf.Rect(margin, margin, page_rect.width-margin, page_rect.height-margin)
        more, _ = story.place(body_rect)
        if more:
            continue
        output = BytesIO()
        writer = pymupdf.DocumentWriter(output)
        try:
            device = writer.begin_page(page_rect)
            story.draw(device)
            writer.end_page()
        finally:
            writer.close()
        with pymupdf.open(stream=output.getvalue(), filetype='pdf') as doc:
            doc.set_metadata({'title':'Resume', 'creator':'JobPilot'})
            return doc.tobytes(garbage=4, deflate=True)
    raise ValueError('Resume cannot fit one readable page; shorten summary or bullets.')
