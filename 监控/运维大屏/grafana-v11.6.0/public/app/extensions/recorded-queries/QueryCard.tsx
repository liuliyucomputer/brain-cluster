import { css } from '@emotion/css';

import { GrafanaTheme2 } from '@grafana/data';
import { secondsToHms } from '@grafana/data/src/datetime/rangeutil';
import { getDataSourceSrv } from '@grafana/runtime';
import { useStyles2 } from '@grafana/ui';

import { RecordedQuery } from '../types';

interface Props {
  recordedQuery: RecordedQuery;
  buttons: JSX.Element[];
}

export const QueryCard = ({ recordedQuery, buttons }: Props) => {
  const styles = useStyles2(getStyles);
  const ds = getDataSourceSrv()?.getInstanceSettings(recordedQuery.queries[0]?.datasource);

  return (
    <div className={styles.alert}>
      {ds?.meta && <img className={styles.media} src={ds.meta.info.logos.small} alt="Query logo" />}

      <div className={styles.body}>
        <div className={styles.info}>
          <div>
            <h2 className={styles.heading}>{recordedQuery.name}</h2>
            <p className={styles.description}>{content(recordedQuery)}</p>
          </div>
          <div className={styles.buttonWrapper}>
            {buttons.map((b, i) => {
              return (
                <div key={`button-${i}`} className={styles.button}>
                  {b}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

const content = (rq: RecordedQuery): string => {
  const content = [`Interval: ${secondsToHms(rq.interval)}`, `Range: Last ${secondsToHms(rq.range)}`];
  const ds = getDataSourceSrv()?.getInstanceSettings(rq.queries[0]?.datasource);
  if (ds !== undefined) {
    content.unshift(ds.name);
  }
  if (rq.description !== '') {
    content.push(`${rq.description}`);
  }
  return content.join(' | ');
};

const getStyles = (theme: GrafanaTheme2) => {
  const borderRadius = theme.shape.borderRadius();

  return {
    info: css({
      display: 'flex',
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      width: '100%',
    }),
    heading: css({
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      width: '100%',
      marginBottom: 0,
      fontSize: theme.typography.size.md,
      letterSpacing: 'inherit',
      lineHeight: theme.typography.body.lineHeight,
      color: theme.colors.text.primary,
      fontWeight: theme.typography.fontWeightMedium,
    }),
    description: css({
      width: '100%',
      margin: theme.spacing(1, 0, 0),
      color: theme.colors.text.secondary,
      lineHeight: theme.typography.body.lineHeight,
    }),
    alert: css({
      flexGrow: 1,
      position: 'relative',
      borderRadius: borderRadius,
      display: 'flex',
      flexDirection: 'row',
      alignItems: 'center',
      background: theme.colors.background.secondary,
      boxShadow: theme.shadows.z1,
      marginBottom: theme.spacing(1),

      '&:before': {
        content: "''",
        position: 'absolute',
        top: 0,
        left: 0,
        bottom: 0,
        right: 0,
        background: theme.colors.background.primary,
        zIndex: -1,
      }
    }),
    body: css({
      color: theme.colors.text.secondary,
      padding: theme.spacing(2),
      flexGrow: 1,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      overflowWrap: 'break-word',
      wordBreak: 'break-word',
    }),
    content: css({
      color: theme.colors.text.secondary,
      paddingTop: theme.spacing(1),
      marginLeft: '26px',
    }),
    media: css({
      marginLeft: theme.spacing(2),
      width: '40px',
    }),
    buttonWrapper: css({
      padding: theme.spacing(1),
      background: 'none',
      display: 'flex',
      alignItems: 'center',
      marginRight: theme.spacing(),
    }),
    button: css({
      marginLeft: theme.spacing(),
    }),
  };
};
