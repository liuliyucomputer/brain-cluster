import { getAppEvents } from "@grafana/runtime";
import { Button, Stack } from "@grafana/ui";

import { notifyApp } from "../../../core/actions";
import { createSuccessNotification } from "../../../core/copy/appNotification";
import { t, Trans } from "../../../core/internationalization";
import { OnSelectQueryType } from "../../../features/explore/QueryLibrary/types";
import { dispatch } from "../../../store/store";
import { ShowConfirmModalEvent } from "../../../types/events";
import { queryLibaryTrackDeleteQuery } from "../QueryLibraryAnalyticsEvents";
import { useDeleteQueryTemplateMutation } from "../api";
import { QueryTemplateRow } from "../types";

export interface QueryLibraryActionsProps {
  onSelectQuery: OnSelectQueryType;
  selectedQueryRow: QueryTemplateRow;
}
export function QueryLibraryActions({
  onSelectQuery,
  selectedQueryRow
}: QueryLibraryActionsProps) {
  const [deleteQueryTemplate] = useDeleteQueryTemplateMutation();

  const onDeleteQuery = (queryUid: string) => {
    const performDelete = (queryUid: string) => {
      deleteQueryTemplate({
        name: queryUid,
        deleteOptions: {},
      });
      dispatch(notifyApp(createSuccessNotification(t('query-library.notifications.query-deleted', 'Query deleted'))));
      queryLibaryTrackDeleteQuery();
    };

    getAppEvents().publish(
      new ShowConfirmModalEvent({
        title: t('query-library.delete-modal.title', 'Delete query'),
        text: t(
          'query-library.delete-modal.body-text',
          "You're about to remove this query from the query library. This action cannot be undone. Do you want to continue?"
        ),
        yesText: t('query-library.delete-modal.confirm-button', 'Delete query'),
        icon: 'trash-alt',
        onConfirm: () => performDelete(queryUid),
      })
    );
  };
  return (
    <Stack wrap="wrap" justifyContent="flex-end">
      <Button variant="destructive" onClick={() => onDeleteQuery(selectedQueryRow.uid ?? '')}>
        <Trans i18nKey="query-library.actions.delete-query-button">
          Delete query
        </Trans>
      </Button>
      <Button onClick={() => onSelectQuery(selectedQueryRow.query)}>
        <Trans i18nKey="query-library.actions.select-query-button">Select query</Trans>
      </Button>
    </Stack>
  )
}
