import { Resource, ResourceForCreate, ResourceList } from 'app/features/apiserver/types';

import { baseAPI as api } from './baseAPI';
import { RequestArg, SandboxSettingsSpec, UpdateRequestArg } from './types';

const BASE_PATH = '/sandbox-settings';

const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    listSandboxSettings: build.query<ResourceList<SandboxSettingsSpec>, void>({
      query: () => ({
        url: BASE_PATH,
      }),
      providesTags: ['SandboxSettingsList'],
    }),
    createSandboxSettings: build.mutation<void, ResourceForCreate<SandboxSettingsSpec>>({
      query: (resource) => ({
        url: BASE_PATH,
        method: 'POST',
        body: resource,
      }),
      invalidatesTags: ['SandboxSettingsList'],
    }),
    getSandboxSettings: build.query<Resource<SandboxSettingsSpec>, RequestArg>({
      query: (queryArg) => ({ url: `${BASE_PATH}/${queryArg.name}`, showErrorAlert: queryArg.showErrorAlert }),
    }),
    deleteSandboxSettings: build.mutation<unknown, RequestArg>({
      query: (queryArg) => ({
        url: `${BASE_PATH}/${queryArg.name}`,
        method: 'DELETE',
        showErrorAlert: queryArg.showErrorAlert,
      }),
    }),
    updateSandboxSettings: build.mutation<Resource<SandboxSettingsSpec>, UpdateRequestArg<SandboxSettingsSpec>>({
      query: (queryArg) => ({
        url: `${BASE_PATH}/${queryArg.name}`,
        method: 'PATCH',
        headers: { 'Content-Type': 'application/merge-patch+json' },
        body: JSON.stringify(queryArg.body),
        showErrorAlert: queryArg.showErrorAlert,
      }),
      invalidatesTags: ['SandboxSettingsList'],
    }),
  }),
  overrideExisting: false,
});
export { injectedRtkApi as generatedAPI };

export const {
  useListSandboxSettingsQuery,
  useCreateSandboxSettingsMutation,
  useGetSandboxSettingsQuery,
  useDeleteSandboxSettingsMutation,
  useUpdateSandboxSettingsMutation,
} = injectedRtkApi;
