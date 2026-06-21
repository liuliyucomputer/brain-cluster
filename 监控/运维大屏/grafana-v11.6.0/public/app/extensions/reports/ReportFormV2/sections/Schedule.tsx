import { t } from 'app/core/internationalization';

import ReportSection from '../ReportSection';

export default function Schedule() {
  return (
    <ReportSection defaultOpen={true} label={t('share-report.schedule.section-title', 'Schedule')}>
      <div></div>
    </ReportSection>
  );
}
