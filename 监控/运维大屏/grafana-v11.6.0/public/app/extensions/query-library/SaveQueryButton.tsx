import { useLocalStorage } from 'react-use';

import { DataQuery } from '@grafana/schema';
import { Badge } from '@grafana/ui';
import { QueryOperationAction } from 'app/core/components/QueryOperationRow/QueryOperationAction';
import { t } from 'app/core/internationalization';
import { useQueryLibraryContext } from 'app/features/explore/QueryLibrary/QueryLibraryContext';

import { QUERY_LIBRARY_LOCAL_STORAGE_KEYS } from './QueryLibraryDrawer';

interface Props {
  query: DataQuery;
}

export function SaveQueryButton({ query }: Props) {
  const { openAddQueryModal } = useQueryLibraryContext();

  const [showQueryLibraryBadgeButton, setShowQueryLibraryBadgeButton] = useLocalStorage(
    QUERY_LIBRARY_LOCAL_STORAGE_KEYS.explore.newButton,
    true
  );

  return showQueryLibraryBadgeButton ? (
    <Badge
      text={t('query-operation.header.save-to-query-library-new', 'New: Save to query library')}
      icon="save"
      color="blue"
      onClick={() => {
        openAddQueryModal(query);
        setShowQueryLibraryBadgeButton(false);
      }}
      style={{ cursor: 'pointer' }}
    />
  ) : (
    <QueryOperationAction
      title={t('query-operation.header.save-to-query-library', 'Save to query library')}
      icon="save"
      onClick={() => {
        openAddQueryModal(query);
      }}
    />
  );
}
