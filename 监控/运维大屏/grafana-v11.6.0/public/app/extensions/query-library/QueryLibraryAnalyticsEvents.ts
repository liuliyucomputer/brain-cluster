import { reportInteraction } from '@grafana/runtime';

const QUERY_LIBRARY_EXPLORE_EVENT = 'query_library_explore_clicked';

export function queryLibraryTrackOpen(context = 'unknown') {
  reportInteraction(QUERY_LIBRARY_EXPLORE_EVENT, {
    item: 'query_library_open',
    context,
  });
}

export function queryLibraryTrackAddQueryOpen(context = 'unknown') {
  reportInteraction(QUERY_LIBRARY_EXPLORE_EVENT, {
    item: 'add_query_modal_shown',
    context,
  });
}

export function queryLibraryTrackAddQuery(datasourceType: string, context = 'unknown') {
  reportInteraction(QUERY_LIBRARY_EXPLORE_EVENT, {
    item: 'add_query',
    type: datasourceType,
    context,
  });
}

export function queryLibaryTrackDeleteQuery() {
  reportInteraction(QUERY_LIBRARY_EXPLORE_EVENT, {
    item: 'delete_query',
  });
}

export function queryLibraryTrackQueryAction(datasourceType: string, context = 'unknown') {
  reportInteraction(QUERY_LIBRARY_EXPLORE_EVENT, {
    item: 'query_action',
    type: datasourceType,
    context,
  });
}

export function queryLibraryTrackAddOrEditDescription() {
  reportInteraction(QUERY_LIBRARY_EXPLORE_EVENT, {
    item: 'add_or_edit_description',
  });
}

export function queryLibraryTrackFilterDatasource() {
  reportInteraction(QUERY_LIBRARY_EXPLORE_EVENT, {
    item: 'filter_datasource',
  });
}
