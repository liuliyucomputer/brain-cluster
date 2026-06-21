import { SyntheticEvent, useEffect, useState } from 'react';
import Skeleton from 'react-loading-skeleton';

import { reportInteraction } from '@grafana/runtime';
import { InlineField, InlineSwitch, TextLink, Text } from '@grafana/ui';
import { t, Trans } from 'app/core/internationalization';
import { CatalogPlugin } from 'app/features/plugins/admin/types';
import { shouldLoadPluginInFrontendSandbox } from 'app/features/plugins/sandbox/sandbox_plugin_loader_registry';

import { SandboxSettingsSpec } from './api/types';
import { useCreateOrUpdateSandboxSettings, useIsSandboxEligible, useSandboxSettings } from './hooks';

export const FrontendSandboxSwitch = ({ plugin }: { plugin: CatalogPlugin }) => {
  const [settings, isLoadingSettings] = useSandboxSettings(plugin.id);
  const [submitData, requestStatus] = useCreateOrUpdateSandboxSettings(plugin.id, Boolean(settings));
  // we make sure we take in consideration the configuration file
  // but the stored setting has priority
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!settings) {
      // default to oss while loading or when there are no settings stored
      shouldLoadPluginInFrontendSandbox({ pluginId: plugin.id, isAngular: false }).then(setIsEnabled);
      return
    }
    setIsEnabled(settings.enabled);
  }, [settings, plugin.id]);

  useEffect(() => {
    if (!requestStatus.isLoading && isLoading) {
      setIsLoading(false);
      // a browser reload is required for the frontend sandbox
      // to take effect in the plugin
      window.location.reload();
    }
    if (requestStatus?.data?.spec?.enabled !== undefined) {
      setIsEnabled(requestStatus.data.spec.enabled);
    }
  }, [requestStatus, isLoading]);

  if (isLoadingSettings) {
    return <Skeleton height={40} width={200} />;
  }

  const handleChange = async (event: SyntheticEvent<HTMLInputElement>) => {
    if (requestStatus.isLoading || isLoading) {
      return;
    }
    setIsLoading(true);
    const value = event.currentTarget.checked;
    reportInteraction("plugins_sandbox_switch", {
      plugin: plugin.id,
      enabled: value,
      creator_team: "grafana_plugins_catalog",
      schema_version: "1.0.0"
    });
    const payload: SandboxSettingsSpec = {
      plugin: plugin.id,
      enabled: value,
      apiAllowList: [],
    };
    submitData(payload);
  };

  return (
    <>
      <InlineField
        interactive={true}
        tooltip={FrontendSandboxSwitchTooltip}
        label={t('plugins.sandbox.enable-sandbox-label', 'Frontend Sandbox')}
        disabled={isLoading}
      >
        <InlineSwitch onChange={handleChange} value={isEnabled} />
      </InlineField >

    </>
  );
};

export const FrontendSandboxSwitchWrapper = ({ plugin }: { plugin?: CatalogPlugin }) => {
  const isSandboxElegible = useIsSandboxEligible(plugin);
  if (!plugin || !plugin?.id || !isSandboxElegible) {
    return null;
  }

  return <FrontendSandboxSwitch plugin={plugin} />;
};


function FrontendSandboxSwitchTooltip() {
  return (
    <Text color="primary" element="p">
      <Trans i18nKey="plugins.sandbox.enable-sandbox-tooltip">
        The frontend sandbox runs frontend code in isolation, restricting access to global browser scope and limiting UI modifications to the plugin area.
      </Trans>
      {' '}
      <TextLink href='https://grafana.com/docs/grafana/next/administration/plugin-management/#plugin-frontend-sandbox' inline external weight='light'
      >
        <Trans i18nKey="plugins.sandbox.enable-sandbox-tooltip-link">
          Read more
        </Trans>
      </TextLink>
    </Text>
  )
}
