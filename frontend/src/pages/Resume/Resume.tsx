import ResumeUpload from '../../components/ResumeUpload/ResumeUpload';
import PageHeader from '../../components/ui/PageHeader';
import Icon from '../../components/ui/Icon';
export default function Resume() {
    return <>
    <PageHeader eyebrow="THE STARTING POINT" title="Your story starts here." description="Upload your resume and turn your experience into readable text."/>
    <div className="content-with-aside">
    <ResumeUpload />
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
    <p>Your PDF and extracted text are saved to your account on this server. Scanned-image OCR and structured parsing are not available yet.</p>
    </section>
    </aside>
    </div>
    </>;
}
