import { get } from 'lodash';

import { config } from '@grafana/runtime';
import { registerPluginSubtitleExtension } from 'app/features/plugins/admin/components/PluginSubtitle';
import {
  setSandboxEnabledCheck,
  isPluginFrontendSandboxEnabled as isPluginFrontendSandboxEnabledInOss,
} from 'app/features/plugins/sandbox/sandbox_plugin_loader_registry';

import { FrontendSandboxSwitchWrapper } from './FrontendSandboxSwitch';
import { apiRequest } from './api/baseAPI';
import { SandboxSettingsSpec } from './api/types';

let cache: { [pluginId: string]: boolean } | undefined;

async function shouldLoadPluginInFrontendSandbox(params: { pluginId: string }): Promise<boolean> {
  if (cache) {
    return !!cache[params.pluginId];
  }
  if (!config.bootData.user.isSignedIn) {
    // If the user is not signed in, fallback to the OSS check
    return isPluginFrontendSandboxEnabledInOss(params);
  }
  const settingsList = await apiRequest<{ items?: Array<{ spec: SandboxSettingsSpec }> }>({
    url: `/sandbox-settings`,
    showErrorAlert: false,
  });
  if ('error' in settingsList) {
    const status = `${get(settingsList, 'error.status')}`;
    if (status.startsWith('4')) {
      // 4xx status codes
      // If the sandbox settings are not found in storage, fallback to the OSS check
      return await isPluginFrontendSandboxEnabledInOss(params);
    }
    console.error('Error fetching sandbox settings', settingsList.error);
    return false;
  }
  cache = {};
  if (!settingsList.data.items) {
    return false;
  }
  for (const item of settingsList.data.items) {
    cache[item.spec.plugin] = item.spec.enabled;
  }
  return !!cache[params.pluginId];
}

export function initSandboxPluginLoaderRegistry() {
  cache = undefined;
  setSandboxEnabledCheck(shouldLoadPluginInFrontendSandbox);
  registerPluginSubtitleExtension(FrontendSandboxSwitchWrapper);
}
