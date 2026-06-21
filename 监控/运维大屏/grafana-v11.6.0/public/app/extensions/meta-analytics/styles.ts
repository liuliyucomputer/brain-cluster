import { css } from '@emotion/css';

import { GrafanaTheme2 } from '@grafana/data';
import { stylesFactory } from '@grafana/ui';

export interface InsightsStyles {
  tabContent: string;
  tabsBar: string;
  graphContainer: string;
  panelContent: string;
  userBoxesContainer: string;
  userBox: string;
  userName: string;
  tableContainer: string;
  tableHeader: string;
  userIcon: string;
}

export const getInsightsStyles = stylesFactory((theme: GrafanaTheme2): InsightsStyles => {
  const containerBg = theme.colors.background.secondary;

  return {
    tabContent: css({
      height: '100%',
    }),
    tabsBar: css({
      paddingLeft: theme.spacing(2),
      margin: theme.spacing(3, -1, -3, -3),
    }),
    graphContainer: css({
      marginTop: theme.spacing(2),
      backgroundColor: containerBg,
    }),
    panelContent: css({
      contain: 'none',
    }),
    userBoxesContainer: css({
      display: 'flex',
      marginTop: theme.spacing(3),

      '> div + div': {
        marginLeft: theme.spacing(2),
      }
    }),
    userBox: css({
      padding: theme.spacing(2),
      flex: 1,
      textAlign: 'center',
      backgroundColor: containerBg,
      borderRadius: theme.shape.radius.default,

      'button, img': {
        margin: theme.spacing(0, 0, 1, 0),
      }
    }),
    userName: css({
      fontWeight: theme.typography.fontWeightBold,
    }),
    tableContainer: css({
      marginTop: theme.spacing(3),
      backgroundColor: containerBg,
      paddingBottom: theme.spacing(1),
      borderRadius: theme.shape.radius.default,

      "[role='cell']:first-child > div": {
        padding: '4px',
      },
      "[role='columnheader']:first-child": {
        height: '33px',
      },
      "[role='row']:not(:only-child):nth-child(odd)": {
        backgroundColor: theme.colors.background.primary,
      }
    }),
    tableHeader: css({
      padding: theme.spacing(0, 2, 0.5, 2),
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',

      h4: {
        marginBottom: '0px',
        padding: theme.spacing(3, 0),
      }
    }),
    userIcon: css({
      margin: '0 0',
      width: '26px',
      height: '26px',
      lineHeight: '20px',

      '& > *': {
        width: '26px',
        height: '26px',
        lineHeight: '20px',
      }
    }),
  };
});
