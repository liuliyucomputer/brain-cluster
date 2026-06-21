import { DataQuery } from '@grafana/schema';
import { Modal } from '@grafana/ui';
import { t } from 'app/core/internationalization';

import { queryLibraryTrackAddQuery } from './QueryLibraryAnalyticsEvents';
import { QueryTemplateForm } from './QueryTemplateForm';

type Props = {
  isOpen: boolean;
  close: () => void;
  onSave?: () => void;
  query?: DataQuery;
  context?: string;
};

export function AddToQueryLibraryModal({ query, close, isOpen, context, onSave }: Props) {
  return (
    <Modal
      title={t('explore.query-template-modal.add-title', 'Add query to Query Library')}
      isOpen={isOpen}
      onDismiss={() => close()}
    >
      <QueryTemplateForm
        onCancel={() => {
          close();
        }}
        onSave={(isSuccess) => {
          if (isSuccess) {
            close();
            queryLibraryTrackAddQuery(query?.datasource?.type || '', context);
            onSave?.();
          }
        }}
        queryToAdd={query!}
      />
    </Modal>
  );
}
