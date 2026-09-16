import { Link } from 'react-router-dom';
import Icon, { type IconName } from './Icon';
export default function ComingSoon({ icon, title, description, steps }: {
    icon: IconName;
    title: string;
    description: string;
    steps: string[];
}) {
    return <section className="card coming-soon">
    <div className="empty-illustration">
    <span />
    <span />
    <div>
    <Icon name={icon} size={38}/>
    </div>
    </div>
    <span className="pill neutral">ON THE ROADMAP</span>
    <h2>{title}</h2>
    <p>{description}</p>
    <Link className="btn btn-primary" to="/resume">Prepare your resume <Icon name="arrow" size={18}/>
    </Link>
    <div className="future-steps">{steps.map((step, index) => <div key={step}>
        <span>0{index + 1}</span>{step}</div>)}</div>
    </section>;
}
