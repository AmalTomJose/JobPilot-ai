import { useEffect, useRef } from 'react';

export default function ConfirmDialog({title, description, confirmLabel, onConfirm, onCancel}: {
    title: string; description: string; confirmLabel?: string; onConfirm?: () => void; onCancel: () => void;
}) {
    const dialog = useRef<HTMLDialogElement>(null);
    useEffect(() => {
        const element = dialog.current;
        element?.showModal();
        return () => element?.close();
    }, []);
    return <dialog ref={dialog} className="card review-dialog" aria-labelledby="confirm-title" aria-describedby="confirm-description" onCancel={event => { event.preventDefault(); onCancel(); }}>
        <h2 id="confirm-title">{title}</h2><p id="confirm-description">{description}</p><div className="button-row"><button autoFocus type="button" className="btn btn-primary" onClick={onCancel}>Keep reviewing</button>{onConfirm && <button type="button" className="btn btn-secondary" onClick={onConfirm}>{confirmLabel}</button>}</div>
    </dialog>;
}
