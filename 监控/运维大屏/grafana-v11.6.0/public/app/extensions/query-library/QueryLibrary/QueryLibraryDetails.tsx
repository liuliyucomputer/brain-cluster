import { css } from "@emotion/css";
import { useId, useState } from "react";
import Skeleton from "react-loading-skeleton";

import { dateTime, GrafanaTheme2 } from "@grafana/data";
import { Avatar, Box, Field, IconButton, Input, Modal, Stack, Text, useStyles2 } from "@grafana/ui";
import { attachSkeleton, SkeletonComponent } from "@grafana/ui/src/unstable";

import { t } from "../../../core/internationalization";
import { queryLibraryTrackAddOrEditDescription } from "../QueryLibraryAnalyticsEvents";
import { QueryTemplateForm } from "../QueryTemplateForm";
import { QueryTemplateRow } from "../types";
import { useDatasource } from "../utils/useDatasource";

export interface QueryDetailsProps {
  query: QueryTemplateRow
}
function QueryLibraryDetailsComponent({ query }: QueryDetailsProps) {
  const [editFormOpen, setEditFormOpen] = useState(false);
  const datasourceApi = useDatasource(query.datasourceRef);
  const formattedTime = dateTime(query.createdAtTimestamp).toLocaleString();

  const AUTHOR_ID = useId();
  const DATASOURCE_ID = useId();
  const DATE_ADDED_ID = useId();
  const styles = useStyles2(getStyles);

  return (
    <>
      <Box minWidth={0}>
        <Box display="flex" gap={1} alignItems="center" justifyContent="space-between" marginBottom={2}>
          <Stack gap={1} alignItems="center" minWidth={0}>
            <img
              className={styles.logo}
              src={datasourceApi?.meta.info.logos.small || 'public/img/icn-datasource.svg'}
              alt={datasourceApi?.type}
            />
            <Text variant="h5" truncate>{query.description ?? ''}</Text>
          </Stack>
          <IconButton
            onClick={() => {
              setEditFormOpen(true);
              queryLibraryTrackAddOrEditDescription();
            }}
            name="pen"
            tooltip={t('query-library.query-details.edit-button', 'Edit query')}
          />
        </Box>
        <code className={styles.query}>
          {query.queryText}
        </code>
        <Field label={t('query-library.query-details.datasource', 'Datasource')}>
          <Input readOnly id={DATASOURCE_ID} value={query.datasourceName} />
        </Field>
        <Field label={t('query-library.query-details.author', 'Author')}>
          <Input readOnly id={AUTHOR_ID} prefix={
            <Box marginRight={0.5}>
              <Avatar width={2} height={2} src={query.user?.avatarUrl || 'https://secure.gravatar.com/avatar'} alt="" />
            </Box>
          } value={query.user?.displayName} />
        </Field>
        <Field label={t('query-library.query-details.date-added', 'Date added')}>
          <Input readOnly id={DATE_ADDED_ID} value={formattedTime} />
        </Field>
      </Box>
      <Modal
        title={t('query-library.edit-modal.title', 'Edit query')}
        isOpen={editFormOpen}
        onDismiss={() => setEditFormOpen(false)}
      >
        <QueryTemplateForm
          onCancel={() => setEditFormOpen(false)}
          templateData={query}
          onSave={() => {
            setEditFormOpen(false);
          }}
        />
      </Modal>
    </>
  )
}

const QueryLibraryDetailsSkeleton: SkeletonComponent = ({ rootProps }) => {
  const skeletonStyles = useStyles2(getSkeletonStyles);
  return (
    <Box minWidth={0} {...rootProps}>
      <Stack direction="column" gap={2}>
        <Stack gap={1} alignItems="center" minWidth={0}>
          <Skeleton circle width={24} height={24} containerClassName={skeletonStyles.icon} />
          <Skeleton width={120} />
        </Stack>

        <Skeleton height={32} />

        <Box>
          <Skeleton width={60} />
          <Skeleton height={32} />
        </Box>

        <Box>
          <Skeleton width={60} />
          <Skeleton height={32} />
        </Box>

        <Box>
          <Skeleton width={60} />
          <Skeleton height={32} />
        </Box>
      </Stack>
    </Box>
  )
}

export const QueryLibraryDetails = attachSkeleton(QueryLibraryDetailsComponent, QueryLibraryDetailsSkeleton);

const getSkeletonStyles = () => ({
  icon: css({
    display: 'block',
    lineHeight: 1,
  })
})

const getStyles = (theme: GrafanaTheme2) => ({
  query: css({
    backgroundColor: theme.colors.background.canvas,
    display: 'block',
    margin: theme.spacing(0, 0, 2, 0),
    overflowWrap: 'break-word',
    padding: theme.spacing(1),
    whiteSpace: 'pre-wrap',
  }),
  logo: css({
    width: '24px',
  }),
})
