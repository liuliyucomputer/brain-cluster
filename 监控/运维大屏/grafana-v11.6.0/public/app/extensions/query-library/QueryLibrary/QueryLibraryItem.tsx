import { css } from "@emotion/css";
import Skeleton from "react-loading-skeleton";

import { GrafanaTheme2 } from "@grafana/data";
import { Stack, Text, useStyles2 } from "@grafana/ui";
import { attachSkeleton, SkeletonComponent } from "@grafana/ui/src/unstable";

import { QueryTemplateRow } from "../types";
import { useDatasource } from "../utils/useDatasource";

export interface QueryListItemProps {
  isSelected?: boolean;
  onSelectQueryRow: (query: QueryTemplateRow) => void;
  queryRow: QueryTemplateRow;
}

const RADIO_GROUP_NAME = 'query-library-list';

function QueryLibraryItemComponent({ isSelected, onSelectQueryRow, queryRow }: QueryListItemProps) {
  const datasourceApi = useDatasource(queryRow.datasourceRef);
  const styles = useStyles2(getStyles);

  return (
    <label className={styles.label} htmlFor={queryRow.uid}>
      <input
        // only the selected item should be tabbable
        // arrow keys should navigate between items
        tabIndex={isSelected ? 0 : -1}
        type="radio"
        id={queryRow.uid}
        name={RADIO_GROUP_NAME}
        className={styles.input}
        onChange={() => onSelectQueryRow(queryRow)}
        checked={isSelected}
      />
      <Stack alignItems="center">
        <img
          className={styles.logo}
          src={datasourceApi?.meta.info.logos.small || 'public/img/icn-datasource.svg'}
          alt={datasourceApi?.type}
        />
        <Text truncate>{queryRow.description ?? ''}</Text>
      </Stack>
    </label>
  )
}

const QueryLibraryItemSkeleton: SkeletonComponent = ({ rootProps }) => {
  const styles = useStyles2(getStyles);
  const skeletonStyles = useStyles2(getSkeletonStyles);
  return (
    <div className={styles.label} {...rootProps}>
      <div className={skeletonStyles.wrapper}>
        <Skeleton containerClassName={skeletonStyles.icon} circle width={16} height={16} />
        <Skeleton width={120} />
      </div>
    </div>
  )
}

const getSkeletonStyles = (theme: GrafanaTheme2) => ({
  wrapper: css({
    alignItems: 'center',
    display: 'flex',
    gap: theme.spacing(1),
    overflow: 'hidden',
  }),
  icon: css({
    display: 'block',
    lineHeight: 1,
  }),
});

export const QueryLibraryItem = attachSkeleton(QueryLibraryItemComponent, QueryLibraryItemSkeleton);

const getStyles = (theme: GrafanaTheme2) => ({
  input: css({
    cursor: 'pointer',
    inset: 0,
    opacity: 0,
    position: 'absolute',
  }),
  label: css({
    padding: theme.spacing(2, 2, 2, 1),
    position: 'relative',

    ':has(:checked)': {
      backgroundColor: theme.colors.action.selected,
    },

    ':has(:focus-visible)': css({
      backgroundColor: theme.colors.action.hover,
      outline: `2px solid ${theme.colors.primary.main}`,
      outlineOffset: '-2px',
    }),
  }),
  logo: css({
    width: '16px',
  })
})
