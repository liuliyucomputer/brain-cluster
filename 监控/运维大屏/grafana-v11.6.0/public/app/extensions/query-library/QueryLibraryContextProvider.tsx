import { PropsWithChildren, useCallback, useMemo, useState } from 'react';

import { config } from '@grafana/runtime';
import { DataQuery } from '@grafana/schema';
import { QueryLibraryContext } from 'app/features/explore/QueryLibrary/QueryLibraryContext';

import { type OnSelectQueryType } from '../../features/explore/QueryLibrary/types';

import { AddToQueryLibraryModal } from './AddToQueryLibraryModal';
import {
  queryLibraryTrackAddQueryOpen,
  queryLibraryTrackOpen,
  queryLibraryTrackQueryAction,
} from './QueryLibraryAnalyticsEvents';
import { QueryLibraryDrawer } from './QueryLibraryDrawer';
import { SaveQueryButton } from './SaveQueryButton';

export function QueryLibraryContextProvider({ children }: PropsWithChildren) {
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [activeDatasources, setActiveDatasources] = useState<string[]>([]);
  const [isAddQueryModalOpen, setIsAddQueryModalOpen] = useState<boolean>(false);
  const [activeQuery, setActiveQuery] = useState<DataQuery | undefined>(undefined);
  // need to curry the no-op due to the special setState((prevState) => {}) pattern
  const [onSelectQuery, setOnSelectQuery] = useState<OnSelectQueryType>(() => () => {});
  const [context, setContext] = useState('unknown');
  const [onSave, setOnSave] = useState<(() => void) | undefined>(undefined);

  const openDrawer = useCallback(
    (datasourceFilters: string[], onSelectQuery: OnSelectQueryType, options?: { context?: string }) => {
      setActiveDatasources(datasourceFilters);
      // need to curry our function due to the special setState((prevState) => {}) pattern
      setOnSelectQuery(() => onSelectQuery);
      setIsDrawerOpen(true);
      setContext(options?.context || 'unknown');
      queryLibraryTrackOpen(options?.context);
    },
    []
  );

  const closeDrawer = useCallback(() => {
    setActiveDatasources([]);
    // need to curry the no-op due to the special setState((prevState) => {}) pattern
    setOnSelectQuery(() => () => {});
    setIsDrawerOpen(false);
  }, []);

  const openAddQueryModal = useCallback((query: DataQuery, options?: { onSave?: () => void; context?: string }) => {
    setActiveQuery(query);
    setIsAddQueryModalOpen(true);
    setContext(options?.context || 'unknown');
    setOnSave(options?.onSave);
    queryLibraryTrackAddQueryOpen(options?.context);
  }, []);

  const closeAddQueryModal = useCallback(() => {
    setActiveQuery(undefined);
    setIsAddQueryModalOpen(false);
    setOnSave(undefined);
  }, []);

  const contextVal = useMemo(
    () => ({
      isDrawerOpen,
      openDrawer,
      closeDrawer,
      openAddQueryModal,
      closeAddQueryModal,
      renderSaveQueryButton: (query: DataQuery) => <SaveQueryButton query={query} />,
      queryLibraryEnabled: Boolean(config.featureToggles.queryLibrary),
    }),
    [isDrawerOpen, openDrawer, closeDrawer, openAddQueryModal, closeAddQueryModal]
  );

  return (
    <QueryLibraryContext.Provider value={contextVal}>
      {children}
      <QueryLibraryDrawer
        isOpen={isDrawerOpen}
        close={closeDrawer}
        activeDatasources={activeDatasources}
        onSelectQuery={(query) => {
          onSelectQuery(query);
          closeDrawer();
          queryLibraryTrackQueryAction(query.datasource?.type || 'unknown', context);
        }}
      />
      <AddToQueryLibraryModal
        isOpen={isAddQueryModalOpen}
        close={closeAddQueryModal}
        query={activeQuery}
        onSave={onSave}
        context={context}
      />
    </QueryLibraryContext.Provider>
  );
}
