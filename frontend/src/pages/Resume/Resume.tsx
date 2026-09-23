import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import ResumeDraftPanel from '../../components/ResumeUpload/ResumeDraftPanel';
import ResumeUpload from '../../components/ResumeUpload/ResumeUpload';
import PageHeader from '../../components/ui/PageHeader';
import Icon from '../../components/ui/Icon';
export default function Resume() {
    const [params, setParams] = useSearchParams();
    const id = Number(params.get('id'));
    const selectedId = Number.isSafeInteger(id) && id > 0 ? id : null;
    const [refreshKey, setRefreshKey] = useState(0);
    const selectResume = (resumeId: number) => setParams({id: String(resumeId)});
    return <>
    <PageHeader eyebrow="THE STARTING POINT" title="Your story starts here." description="Upload your resume and turn your experience into readable text."/>
    <div className="content-with-aside">
    <ResumeUpload onUploaded={resume => { selectResume(resume.id); setRefreshKey(value => value + 1); }}/>
    <aside className="info-stack">
    <section className="card">
    <span className="feature-icon">
    <Icon name="spark"/>
    </span>
    <h3>A little preparation goes a long way.</h3>
    <p>For the clearest extraction, use a PDF exported from your document editor.</p>
    <ul className="check-list">
    <li>
    <Icon name="check" size={16}/>Select a PDF with selectable text</li>
    <li>
    <Icon name="check" size={16}/>Keep the file under 5 MB</li>
    <li>
    <Icon name="check" size={16}/>Remove password protection</li>
    </ul>
    </section>
    <section className="subtle-card">
    <Icon name="shield"/>
    <h3>What happens to your file?</h3>
    <p>Your PDF and extracted text are saved to your account on this server. Scanned-image OCR is not supported. Structured drafts use rules and preserve uncertain fields for review.</p>
    </section>
    </aside>
    </div>
    <ResumeDraftPanel selectedId={selectedId} onSelect={selectResume} refreshKey={refreshKey}/>
    </>;
}
