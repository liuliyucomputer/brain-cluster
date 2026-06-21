import { t } from 'app/core/internationalization';

import ReportSection from '../ReportSection';

export default function Recipients() {
  return (
    <ReportSection defaultOpen={true} label={t('share-report.recipients.section-title', 'Recipients')}>
      <div></div>
    </ReportSection>
  );
}
