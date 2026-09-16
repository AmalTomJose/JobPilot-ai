import type { CSSProperties } from 'react';
export type IconName = 'grid' | 'file' | 'user' | 'briefcase' | 'send' | 'settings' | 'arrow' | 'upload' | 'check' | 'logout' | 'spark' | 'shield' | 'mail' | 'clock';
const paths: Record<IconName, string> = {
    grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
    file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M8 13h8 M8 17h5',
    user: 'M20 21v-2a7 7 0 0 0-14 0v2 M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
    briefcase: 'M3 7h18v14H3z M8 7V3h8v4 M3 12c6 4 12 4 18 0 M12 12v4',
    send: 'M22 2 9 15 M22 2l-7 20-6-7-7-6z',
    settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2',
    arrow: 'M5 12h14 M13 6l6 6-6 6',
    upload: 'M12 16V3 M7 8l5-5 5 5 M4 16v5h16v-5',
    check: 'M5 12l4 4L19 6',
    logout: 'M9 3H4v18h5 M10 12h11 M17 8l4 4-4 4',
    spark: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z',
    shield: 'M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6z M8 12l3 3 5-6',
    mail: 'M3 5h18v14H3z M3 5l9 8 9-8',
    clock: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 M12 6v6l4 2',
};
export default function Icon({ name, size = 20, style }: {
    name: IconName;
    size?: number;
    style?: CSSProperties;
}) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}>
    <path d={paths[name]}/>
    </svg>;
}
