import PageHeader from '../../components/ui/PageHeader';
import ComingSoon from '../../components/ui/ComingSoon';
export default function Applications() {
    return <>
    <PageHeader eyebrow="EVERY NEXT STEP" title="Applications" description="A future home for your job search, from first interest to final decision."/>
    <ComingSoon icon="send" title="Good things are worth keeping track of." description="Application tracking and automation are not available yet. This space will help you keep your opportunities, progress, and next steps together." steps={['Save an opportunity', 'Review your application', 'Follow your progress']}/>
    </>;
}
