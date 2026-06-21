import { createApi } from '@reduxjs/toolkit/query/react';

import { createBaseQuery } from 'app/api/createBaseQuery';
import { getAPIBaseURL } from 'app/api/utils';

// Currently, we are loading all query templates
// Organizations can have maximum of 1000 query templates
export const QUERY_LIBRARY_GET_LIMIT = 1000;

export const BASE_URL = getAPIBaseURL('querylibrary.grafana.app', 'v0alpha1');

export const queryLibraryApi = createApi({
  baseQuery: createBaseQuery({ baseURL: BASE_URL }),
  reducerPath: 'queryLibraryAPI',
  endpoints: () => ({}),
});
