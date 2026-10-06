"""Add source views while preserving every existing discovery and decision."""
from urllib.parse import urlsplit
from alembic import op
import sqlalchemy as sa
revision = 'c49f70b861da'
down_revision = 'b38e6fa750c9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('discovered_jobs', sa.Column('source_site', sa.String(16), nullable=False, server_default='other'))
    # Keep migration behavior self-contained and bounded; no application imports.
    db = op.get_bind()
    last_id = 0
    while True:
        rows = db.execute(sa.text('SELECT id, job_url FROM discovered_jobs WHERE id > :last ORDER BY id LIMIT 500'), {'last':last_id}).all()
        if not rows:
            break
        for row in rows:
            site = 'other'
            try:
                parsed = urlsplit(row.job_url or '')
                host = (parsed.hostname or '').lower()
                if parsed.scheme in {'http', 'https'} and not parsed.username and not parsed.password:
                    for name, domains in (('linkedin', ('linkedin.com',)), ('naukri', ('naukri.com',)), ('indeed', ('indeed.com', 'indeed.co.in', 'indeed.co.uk', 'indeed.ca', 'indeed.com.au'))):
                        if any(host == domain or host.endswith('.' + domain) for domain in domains):
                            site = name
                            break
            except ValueError:
                pass
            db.execute(sa.text('UPDATE discovered_jobs SET source_site=:site WHERE id=:id'), {'site':site, 'id':row.id})
        last_id = rows[-1].id
    op.create_check_constraint('ck_discovered_site', 'discovered_jobs', "source_site IN ('linkedin', 'naukri', 'indeed', 'other')")
    op.create_index('ix_discovered_owner_site_status', 'discovered_jobs', ['user_id', 'source_site', 'status', 'id'])


def downgrade():
    op.drop_index('ix_discovered_owner_site_status', table_name='discovered_jobs')
    op.drop_constraint('ck_discovered_site', 'discovered_jobs', type_='check')
    op.drop_column('discovered_jobs', 'source_site')
