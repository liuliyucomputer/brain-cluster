import { css } from '@emotion/css';

import { GrafanaTheme2 } from '@grafana/data';
import { useStyles2 } from '@grafana/ui/';
import { UpgradeBox, UpgradeContentVertical } from 'app/core/components/Upgrade/UpgradeBox';

export function UpgradeReport() {
  const styles = useStyles2(getStyles);

  return (
    <div className={styles.container}>
      <UpgradeBox featureName={'reporting'} featureId={'reporting-tab'} />
      <UpgradeContentVertical
        image={'reporting-email.png'}
        featureName={'reporting'}
        featureUrl={'https://grafana.com/docs/grafana/latest/enterprise/reporting'}
        description={
          'Reporting allows you to automatically generate PDFs from any of your dashboards and have Grafana email them to interested parties on a schedule.'
        }
      />
    </div>
  );
}

const getStyles = (theme: GrafanaTheme2) => {
  return {
    container: css({
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-start',
    }),
  };
};
