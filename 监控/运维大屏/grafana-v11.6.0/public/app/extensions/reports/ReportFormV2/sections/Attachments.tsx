import { t } from 'app/core/internationalization';

import ReportSection from '../ReportSection';

export default function Attachments() {
  return (
    <ReportSection label={t('share-report.attachments.section-title', 'Attachments')}>
      <div></div>
    </ReportSection>
  );
}
