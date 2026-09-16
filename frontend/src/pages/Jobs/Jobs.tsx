import PageHeader from '../../components/ui/PageHeader';
import ComingSoon from '../../components/ui/ComingSoon';
export default function Jobs() {
    return <>
    <PageHeader eyebrow="THE RIGHT OPPORTUNITY" title="Discover jobs" description="A future home for opportunities that fit your experience."/>
    <ComingSoon icon="briefcase" title="Your next opportunity belongs here." description="Job email ingestion and matching are on the roadmap. Start with your resume while we build a more focused way to discover your next role." steps={['Bring in job opportunities', 'Match your experience', 'Explore your next move']}/>
    </>;
}
