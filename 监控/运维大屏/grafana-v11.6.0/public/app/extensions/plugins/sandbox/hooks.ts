import { useEffect, useState, useCallback } from 'react';

import { CatalogPlugin } from 'app/features/plugins/admin/types';
import { isPluginFrontendSandboxEligible } from 'app/features/plugins/sandbox/sandbox_plugin_loader_registry';

import {
  useCreateSandboxSettingsMutation,
  useGetSandboxSettingsQuery,
  useUpdateSandboxSettingsMutation,
} from './api/endpoints';
import { SandboxSettingsSpec } from './api/types';

export const useIsSandboxEligible = (plugin?: CatalogPlugin) => {
  const [isElegible, setIsElegible] = useState(false);

  useEffect(() => {
    if (!plugin?.id) {
      setIsElegible(false);
      return;
    }

    isPluginFrontendSandboxEligible({ isAngular: plugin.angularDetected, pluginId: plugin.id }).then(
      (isElegible: boolean) => {
        setIsElegible(isElegible);
      },
    );
  }, [plugin?.id, plugin?.angularDetected]);

  return isElegible;
};

export const useSandboxSettings = (pluginId: string): [SandboxSettingsSpec | undefined, boolean] => {
  const query = useGetSandboxSettingsQuery({ name: pluginId, showErrorAlert: false });
  const isLoading = query?.status === 'pending';

  if (query?.status !== 'fulfilled') {
    return [undefined, isLoading];
  }

  if (!query?.data?.spec) {
    return [undefined, isLoading];
  }

  return [query.data.spec, isLoading];
};

export function useCreateOrUpdateSandboxSettings(name: string, hasData: boolean) {
  const [create, createRequest] = useCreateSandboxSettingsMutation();
  const [update, updateRequest] = useUpdateSandboxSettingsMutation();

  const updateOrCreate = useCallback(
    (data: SandboxSettingsSpec) => {
      if (hasData) {
        return update({ name, body: { metadata: { name }, spec: data } });
      }
      return create({ metadata: { name }, spec: data });
    },
    [create, name, update, hasData],
  );
  return [updateOrCreate, hasData ? updateRequest : createRequest] as const;
}
