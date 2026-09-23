import { Link } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import type { ResumeParse, ResumeSummary } from '../../types/resume-parse.types';
import type { ResumeResponse } from '../../types/resume.types';
import { resumeService } from '../../services/resume.service';
import { apiError } from '../../api/axios';
import Icon from '../ui/Icon';

function SourceText({text, label = "Source block"}: {text: string; label?: string}) {
    return <details className="draft-source"><summary>{label}</summary><pre>{text}</pre></details>;
}

export default function ResumeDraftPanel({selectedId, onSelect, refreshKey}: {
    selectedId: number | null;
    onSelect: (id: number) => void;
    refreshKey: number;
}) {
    const [history, setHistory] = useState<ResumeSummary[]>([]);
    const [historyError, setHistoryError] = useState('');
    const [historyLoading, setHistoryLoading] = useState(true);
    const [historyAttempt, setHistoryAttempt] = useState(0);
    const [resume, setResume] = useState<ResumeResponse | null>(null);
    const [parsed, setParsed] = useState<ResumeParse | null>(null);
    const [loading, setLoading] = useState(false);
    const [parsing, setParsing] = useState(false);
    const [error, setError] = useState('');
    const [attempt, setAttempt] = useState(0);
    const generation = useRef(0);

    useEffect(() => {
        let active = true;
        async function loadHistory() {
            setHistoryLoading(true);
            setHistoryError('');
            try {
                const items = await resumeService.list();
                if (active) setHistory(items);
            } catch (err) {
                if (active) setHistoryError(apiError(err));
            } finally {
                if (active) setHistoryLoading(false);
            }
        }
        void loadHistory();
        return () => { active = false; };
    }, [refreshKey, historyAttempt]);

    useEffect(() => {
        const current = ++generation.current;
        async function loadSelected() {
            setResume(null);
            setParsed(null);
            setError('');
            setParsing(false);
            if (selectedId === null) { setLoading(false); return; }
            setLoading(true);
            try {
                const [document, result] = await Promise.all([
                    resumeService.get(selectedId),
                    resumeService.getParse(selectedId).catch(err => {
                        if (axios.isAxiosError(err) && err.response?.status === 404) return null;
                        throw err;
                    }),
                ]);
                if (generation.current === current) { setResume(document); setParsed(result); }
            } catch (err) {
                if (generation.current === current) setError(apiError(err));
            } finally {
                if (generation.current === current) setLoading(false);
            }
        }
        void loadSelected();
        return () => { generation.current = current + 1; };
    }, [selectedId, attempt]);

    async function buildDraft() {
        if (!resume || parsing) return;
        const current = generation.current;
        setParsing(true);
        setError('');
        try {
            const result = await resumeService.parse(resume.id, parsed?.status === 'completed');
            if (generation.current === current) setParsed(result);
        } catch (err) {
            if (generation.current === current) setError(apiError(err));
        } finally {
            if (generation.current === current) setParsing(false);
        }
    }
    const draft = parsed?.status === 'completed' ? parsed.draft_data : null;
    return <section className="section-block card draft-panel">
        <div className="card-heading"><h2>Your saved resumes</h2><span className="pill teal">Structured drafts</span></div>
        <p className="muted small">Choose a saved document to build or reopen its draft. The latest 50 uploads are listed.</p>
        {historyLoading ? <p role="status" className="form-note">Loading saved resumes…</p> : historyError ? <div className="notice error" role="alert">{historyError}<button className="btn btn-secondary" onClick={() => setHistoryAttempt(value => value + 1)}>Retry</button></div> : history.length === 0 ? <p className="form-note">Your saved resumes will appear here after your first upload.</p> : <div className="field resume-picker">
            <label htmlFor="saved-resume">Saved resume</label>
            <select id="saved-resume" value={selectedId ?? ''} onChange={event => onSelect(Number(event.target.value))}>
                <option value="" disabled>Choose a resume</option>
                {selectedId && !history.some(item => item.id === selectedId) && <option value={selectedId}>Resume #{selectedId}</option>}
                {history.map(item => <option key={item.id} value={item.id}>{item.file_name} · #{item.id}</option>)}
            </select>
        </div>}
        {loading && <p role="status" className="form-note">Opening your saved draft…</p>}
        {error && <div className="notice error" role="alert">{error}<button className="btn btn-secondary" onClick={() => setAttempt(value => value + 1)}>Reload</button></div>}
        {resume && !loading && <>
            <div className="draft-toolbar"><div><h3>{resume.file_name}</h3><p className="form-note">{parsed ? `${parsed.status} · ${parsed.parser_version}` : 'Ready to parse'} · Original text stays unchanged</p></div>
                <button className="btn btn-primary" disabled={parsing || !resume.raw_text?.trim()} onClick={buildDraft}><Icon name="spark" size={17}/>{parsing ? 'Building draft…' : draft ? 'Rebuild draft' : parsed?.status === 'failed' ? 'Retry parsing' : 'Build draft'}</button>
            </div>
            {!resume.raw_text?.trim() && <p className="notice error">This document has no extracted text. Upload a text-based PDF.</p>}
            <SourceText text={resume.raw_text ?? ''} label="Original extracted text"/>
            {parsed?.status === 'failed' && <p className="notice error" role="alert">{parsed.error_message}</p>}
            {draft && <>
                <div className="notice success" role="status">Draft saved. Review and correct the details before confirming your profile.</div>
                {parsed && parsed.warnings.length > 0 && <div className="draft-warnings"><h3>Items to check</h3><ul>{parsed.warnings.map((warning, index) => <li key={`${warning.code}-${index}`}>{warning.message}</li>)}</ul></div>}
                <Link className="btn btn-primary" to={`/resume/${resume.id}/review`}>Review & confirm profile</Link>
                <div className="draft-grid">
                    <section><h3>Contact information</h3><dl className="detail-list">{(['name','email','phone','location'] as const).map(field => <div key={field}><dt>{field}</dt><dd>{draft.contact[field] ?? 'Not identified'}</dd></div>)}</dl>{draft.contact.links.map(link => <p className="small draft-link" key={link}>{link}</p>)}</section>
                    <section><h3>Summary & skills</h3><p className="draft-copy">{draft.summary ?? 'No summary identified.'}</p><div className="draft-skills">{draft.skills.length ? draft.skills.map(skill => <span className="pill teal" key={skill}>{skill}</span>) : <span className="muted small">No skills identified.</span>}</div></section>
                </div>
                <section className="draft-section"><h3>Experience</h3>{!draft.experience.length && <p className="form-note">No experience section identified.</p>}{draft.experience.map((entry,index) => <article className="draft-entry" key={index}><h4>{entry.title ?? 'Title not identified'}</h4><p>{entry.company ?? 'Employer not identified'} · {entry.date_text ?? 'Dates not identified'}</p>{entry.location && <p>{entry.location}</p>}<ul>{entry.description.map((line,i) => <li key={i}>{line}</li>)}</ul><SourceText text={entry.source_text}/></article>)}</section>
                <section className="draft-section"><h3>Education</h3>{!draft.education.length && <p className="form-note">No education section identified.</p>}{draft.education.map((entry,index) => <article className="draft-entry" key={index}><h4>{entry.degree ?? 'Degree not identified'}</h4><p>{entry.institution ?? 'Institution not identified'} · {entry.date_text ?? 'Dates not identified'}</p>{entry.field_of_study && <p>{entry.field_of_study}</p>}<SourceText text={entry.source_text}/></article>)}</section>
                <section className="draft-section"><h3>Projects</h3>{!draft.projects.length && <p className="form-note">No projects section identified.</p>}{draft.projects.map((entry,index) => <article className="draft-entry" key={index}><h4>{entry.name ?? 'Project name not identified'}</h4><ul>{entry.description.map((line,i) => <li key={i}>{line}</li>)}</ul><p>{entry.technologies.join(', ')}</p>{entry.links.map(link => <p key={link} className="draft-link">{link}</p>)}<SourceText text={entry.source_text}/></article>)}</section>
                {draft.unclassified_text && <section className="draft-section"><h3>Additional source text</h3><p className="form-note">Header details and unsupported sections are retained for later review.</p><SourceText text={draft.unclassified_text}/></section>}
            </>}
        </>}
    </section>;
}
