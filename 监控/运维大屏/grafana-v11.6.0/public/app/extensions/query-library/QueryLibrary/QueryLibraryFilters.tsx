import { css } from "@emotion/css";

import { GrafanaTheme2, SelectableValue } from "@grafana/data";
import { FilterInput, InlineField, MultiSelect, Stack, useStyles2 } from "@grafana/ui";

import { t } from "../../../core/internationalization";
import { queryLibraryTrackFilterDatasource } from "../QueryLibraryAnalyticsEvents";

export interface QueryLibraryFiltersProps {
  datasourceFilterOptions: Array<SelectableValue<string>>;
  datasourceFilters: Array<SelectableValue<string>>;
  disabled?: boolean;
  onChangeDatasourceFilters: (datasources: Array<SelectableValue<string>>) => void;
  onChangeSearchQuery: (query: string) => void;
  onChangeUserFilters: (users: Array<SelectableValue<string>>) => void;
  searchQuery: string;
  userFilterOptions: Array<SelectableValue<string>>;
  userFilters: Array<SelectableValue<string>>;
}

const DATASOURCE_FILTER_ID = 'query-library-datasource-filter';
const USER_FILTER_ID = 'query-library-user-filter';

export function QueryLibraryFilters({
  datasourceFilterOptions,
  datasourceFilters,
  disabled,
  onChangeDatasourceFilters,
  onChangeSearchQuery,
  onChangeUserFilters,
  searchQuery,
  userFilterOptions,
  userFilters,
}: QueryLibraryFiltersProps) {
  const styles = useStyles2(getStyles);

  return (
    <Stack direction="column" gap={1}>
      <FilterInput
        disabled={disabled}
        placeholder={t('query-library.filters.search-placeholder', 'Search by data source, query content or description')}
        aria-label={t('query-library.filters.search-placeholder', 'Search by data source, query content or description')}
        value={searchQuery}
        onChange={onChangeSearchQuery}
        escapeRegex={false}
      />
      <Stack gap={1} wrap="wrap">
        <InlineField disabled={disabled} className={styles.filterField} grow shrink htmlFor={DATASOURCE_FILTER_ID} label={t('query-library.filters.datasource-label', 'Datasource name(s)')}>
          <MultiSelect
            inputId={DATASOURCE_FILTER_ID}
            onChange={(items, actionMeta) => {
              onChangeDatasourceFilters(items);
              actionMeta.action === 'select-option' && queryLibraryTrackFilterDatasource();
            }}
            value={datasourceFilters}
            options={datasourceFilterOptions}
          />
        </InlineField>
        <InlineField disabled={disabled} className={styles.filterField} grow shrink htmlFor={USER_FILTER_ID} label={t('query-library.filters.user-label', 'User name(s)')}>
          <MultiSelect
            inputId={USER_FILTER_ID}
            onChange={(items, actionMeta) => {
              onChangeUserFilters(items);
              actionMeta.action === 'select-option' && queryLibraryTrackFilterDatasource();
            }}
            value={userFilters}
            options={userFilterOptions}
          />
        </InlineField>
      </Stack>
    </Stack>
  );
}

const getStyles = (theme: GrafanaTheme2) => ({
  filterField: css({
    margin: 0,
  }),
});
