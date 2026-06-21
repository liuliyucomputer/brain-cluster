import { useLocalStorage } from 'react-use';

import { Drawer } from '@grafana/ui';
import { t } from 'app/core/internationalization';

import { OnSelectQueryType } from '../../features/explore/QueryLibrary/types';

import { QueryLibrary } from './QueryLibrary/QueryLibrary';
import { QueryLibraryExpmInfo } from './QueryLibraryExpmInfo';

type Props = {
  isOpen: boolean;
  // List of datasource names to filter query templates by
  activeDatasources: string[];
  close: () => void;
  onSelectQuery: OnSelectQueryType;
};

export const QUERY_LIBRARY_LOCAL_STORAGE_KEYS = {
  explore: {
    notifyUserAboutQueryLibrary: 'grafana.explore.query-library.notifyUserAboutQueryLibrary',
    newButton: 'grafana.explore.query-library.newButton',
  },
};

/**
 * Drawer with query library feature. Handles its own state and should be included in some top level component.
 */
export function QueryLibraryDrawer({ isOpen, activeDatasources, close, onSelectQuery }: Props) {
  const [notifyUserAboutQueryLibrary, setNotifyUserAboutQueryLibrary] = useLocalStorage(
    QUERY_LIBRARY_LOCAL_STORAGE_KEYS.explore.notifyUserAboutQueryLibrary,
    true
  );

  return (
    isOpen && (
      <Drawer
        title={t('query-library.drawer.title', 'Query library')}
        onClose={close}
        scrollableContent={false}
      >
        <QueryLibraryExpmInfo
          isOpen={notifyUserAboutQueryLibrary || false}
          onDismiss={() => setNotifyUserAboutQueryLibrary(false)}
        />
        <QueryLibrary activeDatasources={activeDatasources} onSelectQuery={onSelectQuery} />
      </Drawer>
    )
  );
}
