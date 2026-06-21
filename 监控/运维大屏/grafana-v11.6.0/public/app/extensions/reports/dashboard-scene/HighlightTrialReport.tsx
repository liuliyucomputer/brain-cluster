import { css } from '@emotion/css';

import { GrafanaTheme2 } from '@grafana/data';
import { useStyles2, LinkButton } from '@grafana/ui/';
import { UpgradeBox } from 'app/core/components/Upgrade/UpgradeBox';

export function HighlightTrialReport() {
  const styles = useStyles2(getStyles);

  return (
    <div className={styles.highlight}>
      <UpgradeBox
        featureId={'reporting-tab'}
        eventVariant={'trial'}
        featureName={'reporting'}
        text={'Create unlimited reports during your trial of Grafana Pro.'}
      />
      <h3>Get started with reporting</h3>
      <h6>
        Reporting allows you to automatically generate PDFs from any of your dashboards and have Grafana email them to
        interested parties on a schedule.
      </h6>
      <LinkButton fill="text" href={'https://grafana.com/docs/grafana/latest/enterprise/reporting'}>
        Learn more
      </LinkButton>
    </div>
  );
}

const getStyles = (theme: GrafanaTheme2) => {
  return {
    highlight: css({
      marginBottom: theme.spacing(3),
      h6: {
        fontWeight: theme.typography.fontWeightLight,
      },
    }),
  };
};
