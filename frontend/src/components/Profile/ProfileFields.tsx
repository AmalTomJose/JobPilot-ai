import { useFieldArray, useFormContext, type Path } from 'react-hook-form';
import { emptyEducation, emptyExperience, emptyProject, type ProfileFormValues } from './profile-form';

function Field({name, label, multiline = false, hint, maxLength = 255, type = 'text'}: {
    name: Path<ProfileFormValues>; label: string; multiline?: boolean; hint?: string; maxLength?: number; type?: string;
}) {
    const { register } = useFormContext<ProfileFormValues>();
    return <div className={`field ${multiline ? 'review-wide' : ''}`}>
        <label htmlFor={name}>{label}</label>
        {multiline ? <textarea id={name} rows={4} aria-describedby={hint ? `${name}-hint` : undefined} maxLength={maxLength} {...register(name)}/> : <input id={name} type={type} aria-describedby={hint ? `${name}-hint` : undefined} maxLength={maxLength} {...register(name)}/>}
        {hint && <span className="form-note" id={`${name}-hint`}>{hint}</span>}
    </div>;
}

export default function ProfileFields() {
    const {control} = useFormContext<ProfileFormValues>();
    const experience = useFieldArray({control, name: 'experience'});
    const education = useFieldArray({control, name: 'education'});
    const projects = useFieldArray({control, name: 'projects'});
    return <>
        <section className="review-section"><span className="eyebrow">01 / THE ESSENTIALS</span><h2>Contact information</h2><p className="form-note">Your professional contact details. This does not change your sign-in email.</p>
            <div className="review-fields">
                <Field name="contact.name" label="Full name"/>
                <Field name="contact.email" label="Contact email" type="email"/>
                <Field name="contact.phone" label="Phone" type="tel"/>
                <Field name="contact.location" label="Location"/>
                <Field name="contact.links" label="Professional links" multiline maxLength={20000} hint="One complete https:// or http:// URL per line."/>
            </div>
        </section>
        <section className="review-section"><span className="eyebrow">02 / YOUR STRENGTHS</span><h2>Summary & skills</h2>
            <div className="review-fields"><Field name="summary" label="Professional summary" multiline maxLength={5000}/><Field name="skills" label="Skills" multiline maxLength={50000} hint="One skill per line. Leave unknown details empty."/></div>
        </section>
        <section className="review-section"><span className="eyebrow">03 / WHERE YOU HAVE BEEN</span><h2>Experience</h2>
            {experience.fields.map((item, index) => <fieldset className="review-entry" key={item.id}><legend>Experience {index + 1}</legend>
                <div className="review-fields">
                    <Field name={`experience.${index}.title`} label="Job title"/>
                    <Field name={`experience.${index}.company`} label="Company"/>
                    <Field name={`experience.${index}.location`} label="Job location"/>
                    <Field name={`experience.${index}.date_text`} label="Employment dates"/>
                    <Field name={`experience.${index}.description`} label="Responsibilities & achievements" multiline maxLength={100000} hint="One item per line. Keep dates in your preferred wording."/>
                </div><button type="button" className="text-link remove-entry" onClick={() => experience.remove(index)}>Remove experience {index + 1}</button>
            </fieldset>)}
            <button type="button" className="btn btn-secondary" disabled={experience.fields.length >= 50} onClick={() => experience.append(emptyExperience())}>Add experience</button>
        </section>
        <section className="review-section"><span className="eyebrow">04 / YOUR FOUNDATIONS</span><h2>Education</h2>
            {education.fields.map((item, index) => <fieldset className="review-entry" key={item.id}><legend>Education {index + 1}</legend>
                <div className="review-fields">
                    <Field name={`education.${index}.institution`} label="Institution"/>
                    <Field name={`education.${index}.degree`} label="Degree or qualification"/>
                    <Field name={`education.${index}.field_of_study`} label="Field of study"/>
                    <Field name={`education.${index}.date_text`} label="Education dates"/>
                </div><button type="button" className="text-link remove-entry" onClick={() => education.remove(index)}>Remove education {index + 1}</button>
            </fieldset>)}
            <button type="button" className="btn btn-secondary" disabled={education.fields.length >= 50} onClick={() => education.append(emptyEducation())}>Add education</button>
        </section>
        <section className="review-section"><span className="eyebrow">05 / WHAT YOU HAVE BUILT</span><h2>Projects</h2>
            {projects.fields.map((item, index) => <fieldset className="review-entry" key={item.id}><legend>Project {index + 1}</legend>
                <div className="review-fields">
                    <Field name={`projects.${index}.name`} label="Project name"/>
                    <Field name={`projects.${index}.description`} label="Project description" multiline maxLength={100000} hint="One item per line."/>
                    <Field name={`projects.${index}.technologies`} label="Project technologies" multiline maxLength={25500} hint="One technology per line."/>
                    <Field name={`projects.${index}.links`} label="Project links" multiline maxLength={20000} hint="One complete https:// or http:// URL per line."/>
                </div><button type="button" className="text-link remove-entry" onClick={() => projects.remove(index)}>Remove project {index + 1}</button>
            </fieldset>)}
            <button type="button" className="btn btn-secondary" disabled={projects.fields.length >= 50} onClick={() => projects.append(emptyProject())}>Add project</button>
        </section>
    </>;
}
