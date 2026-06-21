import { uniqBy } from 'lodash';
import { useEffect, useMemo, useState } from 'react';

import { AppEvents, SelectableValue } from '@grafana/data';
import { getAppEvents } from '@grafana/runtime';
import { Box, Divider, EmptyState, Stack } from '@grafana/ui';

import { t } from '../../../core/internationalization';
import { type OnSelectQueryType } from '../../../features/explore/QueryLibrary/types';
import { useListQueryTemplateQuery } from '../api';
import { convertDataQueryResponseToQueryTemplates } from '../api/mappers';
import { QueryTemplate } from '../api/types';
import { useLoadQueryMetadata, useLoadUsers } from '../utils/dataFetching';
import { searchQueryLibrary } from '../utils/search';

import { QueryLibraryContent } from './QueryLibraryContent';
import { QueryLibraryFilters } from './QueryLibraryFilters';

export interface QueryLibraryProps {
  // list of active datasources to filter the query library by
  activeDatasources: string[];
  onSelectQuery: OnSelectQueryType;
}

export function QueryLibrary({ activeDatasources, onSelectQuery }: QueryLibraryProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [datasourceFilters, setDatasourceFilters] = useState<Array<SelectableValue<string>>>(
    activeDatasources.map((ds) => ({ value: ds, label: ds }))
  );
  const [userFilters, setUserFilters] = useState<Array<SelectableValue<string>>>([]);

  const { data: rawData, isLoading: isQueryTemplatesLoading, error } = useListQueryTemplateQuery({});
  const data = useMemo(() => (rawData ? convertDataQueryResponseToQueryTemplates(rawData) : undefined), [rawData]);
  const loadUsersResult = useLoadUsersWithError(data);
  const userNames = loadUsersResult.data ? loadUsersResult.data.display.map((user) => user.displayName) : [];
  const loadQueryMetadataResult = useLoadQueryMetadataWithError(data, loadUsersResult.data);
  // Filtering right now is done just on the frontend until there is better backend support for this.
  const filteredRows = useMemo(
    () => loadQueryMetadataResult.value ? searchQueryLibrary(
        loadQueryMetadataResult.value,
        searchQuery,
        datasourceFilters.map((f) => f.value || ''),
        userFilters.map((f) => f.value || '')
      ) : undefined,
    [loadQueryMetadataResult.value, searchQuery, datasourceFilters, userFilters]
  );

  const isFiltered = Boolean(searchQuery || datasourceFilters.length > 0 || userFilters.length > 0);
  const isLoading = isQueryTemplatesLoading || loadUsersResult.isLoading || loadQueryMetadataResult.loading;
  const datasourceNames = useMemo(() => {
    return uniqBy(loadQueryMetadataResult.value, 'datasourceName').map((row) => row.datasourceName);
  }, [loadQueryMetadataResult.value]);

  if (error && error instanceof Error) {
    return (
      <EmptyState variant="not-found" message={t('query-library.error-state.title', 'Something went wrong!')}>
        {error.message}
      </EmptyState>
    );
  }

  return (
    <Stack height="100%" direction="column" gap={0}>
      <Box backgroundColor="primary" paddingBottom={2}>
        <QueryLibraryFilters
          datasourceFilterOptions={datasourceNames.map((r) => ({
            value: r,
            label: r
          }))}
          datasourceFilters={datasourceFilters}
          disabled={(isLoading || !filteredRows)}
          onChangeDatasourceFilters={setDatasourceFilters}
          onChangeSearchQuery={setSearchQuery}
          onChangeUserFilters={setUserFilters}
          searchQuery={searchQuery}
          userFilterOptions={userNames.map((r) => ({
            value: r,
            label: r
          }))}
          userFilters={userFilters}
        />
      </Box>
      <Divider spacing={0} />
      <Stack direction="column" flex={1} minHeight={0}>
        {(isLoading || !filteredRows) ? (
          <QueryLibraryContent.Skeleton />
        ) : (
          <QueryLibraryContent isFiltered={isFiltered} onSelectQuery={onSelectQuery} queryRows={filteredRows} />
        )}
      </Stack>
    </Stack>
  )
}

/**
 * Wrap useLoadUsers with error handling.
 * @param data
 */
function useLoadUsersWithError(data: QueryTemplate[] | undefined) {
  const userUIDs = useMemo(() => data?.map((qt) => qt.user?.uid).filter((uid) => uid !== undefined), [data]);
  const loadUsersResult = useLoadUsers(userUIDs);
  useEffect(() => {
    if (loadUsersResult.error) {
      getAppEvents().publish({
        type: AppEvents.alertError.name,
        payload: [
          t('query-library.user-info.error', 'Error attempting to get user info from the library: {{error}}', {
            error: JSON.stringify(loadUsersResult.error),
          }),
        ],
      });
    }
  }, [loadUsersResult.error]);
  return loadUsersResult;
}

/**
 * Wrap useLoadQueryMetadata with error handling.
 * @param queryTemplates
 * @param userDataList
 */
function useLoadQueryMetadataWithError(
  queryTemplates: QueryTemplate[] | undefined,
  userDataList: ReturnType<typeof useLoadUsers>['data']
) {
  const result = useLoadQueryMetadata(queryTemplates, userDataList);

  // useLoadQueryMetadata returns errors in the values so we filter and group them and later alert only one time for
  // all the errors. This way we show data that is loaded even if some rows errored out.
  // TODO: maybe we could show the rows with incomplete data to see exactly which ones errored out. I assume this
  //  can happen for example when data source for saved query was deleted. Would be nice if user would still be able
  //  to delete such row or decide what to do.
  const [values, errors] = useMemo(() => {
    let errors: Error[] = [];
    let values = [];
    if (!result.value) {
      return [undefined, errors];
    } else if (!result.loading) {
      for (const value of result.value!) {
        if (value.error) {
          errors.push(value.error);
        } else {
          values.push(value);
        }
      }
    }
    return [values, errors];
  }, [result]);

  useEffect(() => {
    if (errors.length) {
      getAppEvents().publish({
        type: AppEvents.alertError.name,
        payload: [
          t('query-library.query-template.error', 'Error attempting to load query template metadata: {{error}}', {
            error: JSON.stringify(errors),
          }),
        ],
      });
    }
  }, [errors]);

  return {
    loading: result.loading,
    value: values,
  };
}
