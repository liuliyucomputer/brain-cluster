import { BaseQueryFn, createApi } from '@reduxjs/toolkit/query/react';
import { lastValueFrom } from 'rxjs';

import { BackendSrvRequest, config, getBackendSrv } from '@grafana/runtime';

interface RequestOptions extends BackendSrvRequest {
  manageError?: (err: unknown) => { error: unknown };
  showErrorAlert?: boolean;

  // rtk codegen sets this
  body?: BackendSrvRequest['data'];
}

const baseURL = `/apis/sandboxsettings.grafana.app/v0alpha1/namespaces/${config.namespace}`;

export async function apiRequest<T>(requestOptions: RequestOptions) {
  try {
    const { data: responseData, ...meta } = await lastValueFrom(
      getBackendSrv().fetch<T>({
        ...requestOptions,
        url: baseURL + requestOptions.url,
        showErrorAlert: requestOptions.showErrorAlert,
        data: requestOptions.body,
      })
    );
    return { data: responseData, meta };
  } catch (error) {
    return requestOptions.manageError ? requestOptions.manageError(error) : { error };
  }
}

function createBackendSrvBaseQuery(): BaseQueryFn<RequestOptions> {
  async function backendSrvBaseQuery(requestOptions: RequestOptions) {
    return apiRequest(requestOptions);
  }

  return backendSrvBaseQuery;
}

export const baseAPI = createApi({
  reducerPath: 'sandboxSettingsGeneratedAPI',
  baseQuery: createBackendSrvBaseQuery(),
  tagTypes: ['SandboxSettingsList'],
  endpoints: () => ({}),
});
