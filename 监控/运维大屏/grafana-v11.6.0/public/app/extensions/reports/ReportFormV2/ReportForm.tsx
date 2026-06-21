import { css } from '@emotion/css';
import { useEffect } from 'react';
import { FormProvider, useForm } from 'react-hook-form';

import { GrafanaTheme2 } from '@grafana/data';
import { Button, Divider, Stack, useStyles2, Field } from '@grafana/ui';
import { Input } from '@grafana/ui/src/components/Input/Input';
import { t } from 'app/core/internationalization';
import { ReportBaseV2 } from 'app/extensions/types/reports';
import { isEmail } from 'app/extensions/utils/validators';

import { DEFAULT_EMAIL_MESSAGE } from '../constants';
import { selectors } from '../e2e-selectors/selectors';
import { canEditReport } from '../utils/permissions';

import Attachments from './sections/Attachments';
import EmailConfiguration from './sections/EmailConfiguration';
import Recipients from './sections/Recipients';
import Schedule from './sections/Schedule';
import SelectDashboards from './sections/SelectDashboards';

const REPORT_FORM_SECTIONS = [
  { id: 'select-dashboards', component: SelectDashboards },
  { id: 'schedule', component: Schedule },
  { id: 'email-configuration', component: EmailConfiguration },
  { id: 'recipients', component: Recipients },
  { id: 'attachments', component: Attachments },
];

export const formSchemaValidationRules = () => ({
  name: {
    required: t('share-report.report-name.required', 'Report name is required'),
  },
  replyTo: {
    validate: (val: string | undefined) => {
      if (!val) {
        return true;
      }
      return isEmail(val) || t('share-report.email-configuration.invalid-email', 'Invalid email');
    },
  },
});

const defaultReport: Partial<ReportBaseV2> = {
  message: DEFAULT_EMAIL_MESSAGE,
  addDashboardUrl: true,
  addDashboardImage: false,
};

export default function ReportForm({ report }: { report?: Partial<ReportBaseV2> }) {
  const styles = useStyles2(getStyles);
  const form = useForm<ReportBaseV2>({
    mode: 'onChange',
    defaultValues: {
      ...defaultReport,
      ...report,
    },
  });

  useEffect(() => {
    form.setFocus('name');
  }, [form, form.setFocus]);

  const onSubmit = (data: ReportBaseV2) => {
    console.log(data);
  };

  return (
    <FormProvider {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className={styles.form}
        data-testid={selectors.components.ReportFormDrawer.container}
      >
        <fieldset disabled={!canEditReport} className={styles.container}>
          <Field
            label={t('share-report.report-name.label', 'Report name')}
            required
            error={form.formState.errors.name?.message}
            invalid={!!form.formState.errors.name}
          >
            <Input
              {...form.register('name', formSchemaValidationRules().name)}
              placeholder={report?.name}
              id="report-name"
              type="text"
            />
          </Field>
          <Divider spacing={0} />
          <div className={styles.reportSectionContainer}>
            <Stack direction="column" flex={1}>
              {REPORT_FORM_SECTIONS.map((section, index) => (
                <div key={section.id}>
                  <section.component />
                  {index < REPORT_FORM_SECTIONS.length - 1 && <Divider />}
                </div>
              ))}
            </Stack>
          </div>
          <Divider />
          <ReportActions isFormValid={form.formState.isValid} />
        </fieldset>
      </form>
    </FormProvider>
  );
}

function ReportActions({ isFormValid }: { isFormValid: boolean }) {
  return (
    <Stack justifyContent="space-between">
      <Stack gap={1}>
        <Button variant="secondary" fill="outline" icon="ellipsis-v" />
        <Button variant="secondary" fill="outline">
          {t('share-report.send-preview.button', 'Send preview')}
        </Button>
      </Stack>
      <Stack gap={1}>
        <Button
          type="submit"
          variant="primary"
          disabled={!isFormValid}
          data-testid={selectors.components.ReportFormDrawer.submitButton}
        >
          {t('share-report.schedule-report.button', 'Schedule report')}
        </Button>
        <Button variant="secondary">{t('share-report.save-draft.button', 'Save draft')}</Button>
      </Stack>
    </Stack>
  );
}

const getStyles = (theme: GrafanaTheme2) => {
  return {
    form: css({
      height: '100%',
    }),
    container: css({
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    }),
    reportSectionContainer: css({
      height: '100%',
      marginTop: theme.spacing(2),
    }),
  };
};
