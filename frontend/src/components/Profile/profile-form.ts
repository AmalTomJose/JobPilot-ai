import type { ProfileData } from '../../types/profile.types';

export const emptyExperience = () => ({ title: '', company: '', location: '', date_text: '', description: '' });
export const emptyEducation = () => ({ institution: '', degree: '', field_of_study: '', date_text: '' });
export const emptyProject = () => ({ name: '', description: '', technologies: '', links: '' });
export type ProfileFormValues = {
    contact: { name: string; email: string; phone: string; location: string; links: string };
    summary: string;
    skills: string;
    experience: ReturnType<typeof emptyExperience>[];
    education: ReturnType<typeof emptyEducation>[];
    projects: ReturnType<typeof emptyProject>[];
    confirmed: boolean;
};
const nullable = (value: string) => value.trim() || null;
export const lines = (value: string) => value.split(/\r?\n/).map(item => item.trim()).filter(Boolean);

export function toForm(data: ProfileData): ProfileFormValues {
    return {
        contact: {
            name: data.contact.name ?? '', email: data.contact.email ?? '',
            phone: data.contact.phone ?? '', location: data.contact.location ?? '',
            links: data.contact.links.join('\n'),
        },
        summary: data.summary ?? '', skills: data.skills.join('\n'), confirmed: false,
        experience: data.experience.map(item => ({title: item.title ?? '', company: item.company ?? '', location: item.location ?? '', date_text: item.date_text ?? '', description: item.description.join('\n')})),
        education: data.education.map(item => ({institution: item.institution ?? '', degree: item.degree ?? '', field_of_study: item.field_of_study ?? '', date_text: item.date_text ?? ''})),
        projects: data.projects.map(item => ({name: item.name ?? '', description: item.description.join('\n'), technologies: item.technologies.join('\n'), links: item.links.join('\n')})),
    };
}

export function toProfile(values: ProfileFormValues): ProfileData {
    return {
        contact: {name: nullable(values.contact.name), email: nullable(values.contact.email), phone: nullable(values.contact.phone), location: nullable(values.contact.location), links: lines(values.contact.links)},
        summary: nullable(values.summary), skills: lines(values.skills),
        experience: values.experience.map(item => ({title: nullable(item.title), company: nullable(item.company), location: nullable(item.location), date_text: nullable(item.date_text), description: lines(item.description)})),
        education: values.education.map(item => ({institution: nullable(item.institution), degree: nullable(item.degree), field_of_study: nullable(item.field_of_study), date_text: nullable(item.date_text)})),
        projects: values.projects.map(item => ({name: nullable(item.name), description: lines(item.description), technologies: lines(item.technologies), links: lines(item.links)})),
    };
}
