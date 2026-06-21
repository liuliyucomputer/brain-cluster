import { useForm, FormProvider } from 'react-hook-form';
import { useAsync } from 'react-use';

import { AppEvents } from '@grafana/data';
import { config, getBackendSrv, locationService } from '@grafana/runtime';
import { Button, Alert } from '@grafana/ui';
import { Page } from 'app/core/components/Page/Page';
import { appEvents, contextSrv } from 'app/core/core';
import { t, Trans } from 'app/core/internationalization';


import { AccessControlAction, FooterMode, ReportsSettings, Theme } from '../types';

import { NoRendererInfoBox } from './RenderingWarnings';
import ReportBranding from './ReportBranding';

export const ReportsSettingsPage = () => {
  const {
    value: settings,
    loading,
    error,
  } = useAsync(async () => {
    const settings: ReportsSettings = await getBackendSrv().get('/api/reports/settings');
    // Update default settings after loading
    const defaultSettings = {
      ...settings,
      branding: {
        ...settings.branding,
        emailFooterMode: settings.branding.emailFooterMode || FooterMode.None
      },
      embeddedImageTheme: settings.embeddedImageTheme || Theme.Dark,
      pdfTheme: settings.pdfTheme || Theme.Light,
    };

    reset(defaultSettings);
    return defaultSettings;
  });

  const { handleSubmit, reset, ...formMethods } = useForm({ mode: 'onBlur', defaultValues: settings});

  const submitForm = (reportSettings: ReportsSettings) => {
    const formData = new FormData();

    for (const [field, value] of Object.entries(reportSettings.branding)) {
      if (value instanceof File) {
        reportSettings.branding = {...reportSettings.branding, [field]: value.name };
        formData.append('files', value);
      }
    }
    formData.append('config', JSON.stringify(reportSettings));

    return fetch(`${config.appUrl}api/reports/settings`, { method: 'POST', body: formData }).then((response) => {
      if (response.ok) {
        appEvents.emit(AppEvents.alertSuccess, ['Successfully saved configuration']);
        locationService.push('/reports');
      } else {
        appEvents.emit(AppEvents.alertError, ['Error saving configuration', response.statusText]);
      }
    });
  };

  if (error) {
    return (
      <Page navId="reports-settings" subTitle={t('reporting.settings.settings-subtitle', 'Manage report template settings.')}>
        <Alert title="Error loading settings" severity="error" />
      </Page>
    );
  }

  const canEditSettings = contextSrv.hasPermission(AccessControlAction.ReportingSettingsWrite);

  return (
    <Page navId="reports-settings" subTitle={t('reporting.settings.settings-subtitle', 'Manage report template settings.')}>
      <Page.Contents isLoading={loading}>
        {!config.rendererAvailable ? (
          <NoRendererInfoBox variant="error" />
        ) : (
          <FormProvider {...formMethods} reset={reset} handleSubmit={handleSubmit}>
            <form onSubmit={handleSubmit(submitForm)} style={{ maxWidth: '500px' }}>
              <ReportBranding />
              <Button type="submit" size="md" variant="primary" disabled={!canEditSettings}>
                <Trans i18nKey="reporting.settings.save-button">
                  Save
                </Trans>
              </Button>
            </form>
          </FormProvider>
        )}
      </Page.Contents>
    </Page>
  );
};

export default ReportsSettingsPage;
