import { useFormContext, Controller } from 'react-hook-form';

import { SelectableValue } from '@grafana/data';
import { config } from '@grafana/runtime';
import { Input, Field, RadioButtonGroup, FieldSet, Text, Stack} from '@grafana/ui';
import { contextSrv } from 'app/core/core';
import { t, Trans } from 'app/core/internationalization';
import { ThemePicker } from 'app/features/dashboard/components/ShareModal/ThemePicker';

import { ResourcePicker } from '../shared/ResourcePicker';
import { getResourceUrl } from '../shared/utils/data';
import { AccessControlAction, FooterMode } from '../types';

import { ImagePreview } from './ImagePreview';
import { defaultEmailLogo, defaultReportLogo } from './constants';

const footerModeOptions: SelectableValue[] = [
  { label: t('reporting.settings.sent-by-footer-label', 'Sent By'), value: FooterMode.SentBy },
  { label: t('reporting.settings.none-footer-label', 'None'), value: FooterMode.None },
];

const ReportBranding = () => {
  const { register, control, watch} = useFormContext();

  const watchReportLogo = watch('branding.reportLogoUrl') || defaultReportLogo;
  const watchEmailLogo = watch('branding.emailLogoUrl') || defaultEmailLogo;
  const watchFooterMode = watch('branding.emailFooterMode');
  const canEditSettings = contextSrv.hasPermission(AccessControlAction.ReportingSettingsWrite);

  return (
    <>
      <FieldSet label={t('reporting.settings.attachment-settings-fieldset-label', 'Attachment settings')} disabled={!canEditSettings}>
      <Stack direction='column' gap={2}>
        <Text element={'h4'} >
            <Trans i18nKey="reporting.settings.pdf-header">
                PDF
            </Trans>
          </Text>
          <Stack direction='column' gap={1}>
            <Field
              htmlFor={'reportLogoUrl'}
              label={t('reporting.settings.report-logo-url-field-label', 'Company logo URL')}
              description={t('reporting.settings.report-logo-url-field-description', 'The logo will be displayed in the document footer. Supported formats: png, jpg, gif.')}
            >
              <ResourcePicker name={'branding.reportLogoUrl'} />
            </Field>
            <ImagePreview
              url={watchReportLogo === defaultReportLogo ? defaultReportLogo : getResourceUrl(watchReportLogo)}
              width="60px"
              altText={t('reporting.settings.report-logo-image-preview-altText', 'Company logo preview')}
            />
            {config.featureToggles.newPDFRendering && (<Controller
              render={({ field }) => (
                <ThemePicker
                  description={t('reporting.settings.pdf-theme-picker-description', 'The theme will be applied to the PDF attached to the report.')}
                  selectedTheme={field.value}
                  onChange={field.onChange}
                />
              )}
              control={control}
              name="pdfTheme"
            />
            )}
          </Stack>
          <Text element={'h4'} >
            <Trans i18nKey="reporting.settings.embedded-image-header">
            Embedded image
            </Trans>
          </Text>
          <Stack direction='column' gap={1}>
            <Controller
              render={({ field }) => (
                <ThemePicker
                  description={t('reporting.settings.embedded-image-theme-picker-description', 'The theme will be applied to the dashboard image embedded in the email.')}
                  selectedTheme={field.value}
                  onChange={field.onChange}
                />
              )}
              control={control}
              name="embeddedImageTheme"
            />
          </Stack>
        </Stack>
      </FieldSet>

      <FieldSet label={t('reporting.settings.email-branding-fieldset-label', 'Email branding')} disabled={!canEditSettings}>
        <Field
          htmlFor={'emailLogoUrl'}
          label={t('reporting.settings.email-logo-url-field-label', 'Company logo URL')}
          description={t('reporting.settings.email-logo-url-field-description', 'The logo will be displayed in the email header. Supported formats: png, jpg, gif.')}
        >
          <ResourcePicker name={'branding.emailLogoUrl'} />
        </Field>
        <ImagePreview
          url={watchEmailLogo === defaultEmailLogo ? defaultEmailLogo : getResourceUrl(watchEmailLogo)}
          altText={t('reporting.settings.email-logo-image-preview-altText', 'Company logo preview')}
        />
        <Field label={t('reporting.settings.email-footer-field-label', 'Email footer')}>
          <Controller
            name="branding.emailFooterMode"
            render={({ field: { ref, ...field } }) => <RadioButtonGroup {...field} options={footerModeOptions} />}
            control={control}
          />
        </Field>
        {watchFooterMode === FooterMode.SentBy && (
          <>
            <Field label={t('reporting.settings.footer-link-field-label', 'Footer link text')}>
              <Input {...register('branding.emailFooterText')} id="emailFooterText" placeholder="Grafana" type="text" />
            </Field>
            <Field label={t('reporting.settings.footer-link-url-field-label', 'Footer link URL')}>
              <Input {...register('branding.emailFooterLink')} id="emailFooterLink" placeholder="https://your.site" type="url" />
            </Field>
          </>
        )}
      </FieldSet>
    </>
  );
};

export default ReportBranding;
