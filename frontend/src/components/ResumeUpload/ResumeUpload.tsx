import { useRef, useState } from 'react';
import { resumeService } from '../../services/resume.service';
import type { ResumeResponse } from '../../types/resume.types';
import { apiError } from '../../api/axios';
import Icon from '../ui/Icon';
export default function ResumeUpload({ onUploaded }: { onUploaded?: (resume: ResumeResponse) => void }) {
    const input = useRef<HTMLInputElement>(null);
    const [file, setFile] = useState<File | null>(null);
    const [resume, setResume] = useState<ResumeResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [dragging, setDragging] = useState(false);
    function selectFile(selected?: File) {
        if (loading || !selected)
            return;
        setResume(null);
        setError('');
        setFile(null);
        if (selected.type !== 'application/pdf') {
            setError('Only PDF files are allowed.');
            return;
        }
        if (!selected.size) {
            setError('This file is empty. Please choose another PDF.');
            return;
        }
        if (selected.size > 5 * 1024 * 1024) {
            setError('Choose a PDF that is 5 MB or less.');
            return;
        }
        setFile(selected);
    }
    async function upload() {
        if (!file || loading)
            return;
        setLoading(true);
        setError('');
        setResume(null);
        try {
            const uploaded = await resumeService.uploadResume(file);
            setResume(uploaded);
            onUploaded?.(uploaded);
        }
        catch (err) {
            setError(apiError(err, 'Your resume could not be uploaded. Please try again.'));
        }
        finally {
            setLoading(false);
        }
    }
    return <div>
    <section className="card upload-card">
    <div className="card-heading">
    <h2>Upload a resume</h2>
    <span className="pill neutral">PDF only</span>
    </div>
    <p className="muted">Give your next chapter a starting point.</p>
    <div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); if (!loading)
        setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); selectFile(event.dataTransfer.files[0]); }}>
    <span className="upload-symbol">
    <Icon name="upload" size={29}/>
    </span>
    <h3>Drop your resume here</h3>
    <p>or choose a file from your computer</p>
    <button className="btn btn-secondary" type="button" disabled={loading} onClick={() => input.current?.click()}>Browse files</button>
    <span className="small muted">PDF · Maximum 5 MB · Text-based documents</span>
    <input className="sr-only" aria-label="Choose a resume PDF" ref={input} type="file" accept="application/pdf,.pdf" disabled={loading} onChange={event => { selectFile(event.target.files?.[0]); event.target.value = ''; }}/>
    </div>{file && <div className="selected-file">
        <span className="feature-icon">
        <Icon name="file"/>
        </span>
        <div>
        <strong>{file.name}</strong>
        <span>{(file.size / 1024).toFixed(0)} KB · Ready to extract</span>
        </div>
        <button aria-label="Remove selected file" className="icon-button" disabled={loading} onClick={() => { setFile(null); setResume(null); setError(''); }}>×</button>
        </div>}{error && <div className="notice error" role="alert">{error}</div>}<div className="upload-footer">
    <span>
    <Icon name="shield" size={16}/>Saved to your account</span>
    <button className="btn btn-primary" disabled={!file || loading || !!resume} onClick={upload}>{loading ? 'Uploading & extracting…' : resume ? 'Upload complete' : 'Upload & extract'}<Icon name={resume ? 'check' : 'arrow'} size={17}/>
    </button>
    </div>
    <p className="form-note">Your saved uploads are available in the list below.</p>
    </section>{resume && <section className="card extraction-result">
        <div className="notice success" role="status">
        <Icon name="check" size={18}/>Resume saved and text extracted successfully.</div>
        <h2>Your text is ready.</h2>
        <p className="muted">{resume.file_name} · Saved {new Date(resume.created_at).toLocaleDateString()}</p>
        <details>
        <summary>Preview extracted text</summary>
        <pre>{resume.raw_text}</pre>
        </details>
        <p className="form-note">This is the original extracted text. Build a structured draft below.</p>
        </section>}</div>;
}
