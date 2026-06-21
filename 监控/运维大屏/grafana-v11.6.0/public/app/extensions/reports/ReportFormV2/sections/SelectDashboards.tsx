import { css } from '@emotion/css';
import { useEffect, useState } from 'react';
import { Controller, useFieldArray, useFormContext } from 'react-hook-form';
import { useMedia } from 'react-use';

import { GrafanaTheme2, isEmptyObject, makeTimeRange, RawTimeRange, VariableHide } from '@grafana/data';
import { config } from '@grafana/runtime';
import {
  Alert,
  Button,
  CollapsableSection,
  Divider,
  Field,
  IconButton,
  LinkButton,
  Stack,
  TimeRangeInput,
  useStyles2,
  useTheme2,
} from '@grafana/ui';
import { t } from 'app/core/internationalization';
import { useDispatch } from 'app/types';

import { DashboardPicker, DashboardPickerDTO } from '../../../../core/components/Select/DashboardPicker';
import { variableAdapters } from '../../../../features/variables/adapters';
import { hasOptions } from '../../../../features/variables/guard';
import { getVariablesByKey } from '../../../../features/variables/state/selectors';
import { VariableModel } from '../../../../features/variables/types';
import { ReportBaseV2, ReportDashboardV2 } from '../../../types';
import { getRange } from '../../../utils/time';
import { selectors } from '../../e2e-selectors/selectors';
import { initVariables } from '../../state/actions';
import { canEditReport } from '../../utils/permissions';
import { refreshOnTimeRange, toReportVariables } from '../../utils/variables';
import ReportSection from '../ReportSection';

interface SelectDashboardProps {
  index: number;
  dataTestId?: string;
  onRemoveClick: () => void;
}

const defaultDashboard: ReportDashboardV2 = {
  dashboard: undefined,
  timeRange: {
    from: '',
    to: '',
  },
  reportVariables: {},
};

const isEmptyDashboard = (dashboard: ReportDashboardV2) => !dashboard.dashboard?.uid;

// const getTimeRange = (timeRange: ReportTimeRange, fallback: ReportTimeRange) => {
//   if (!timeRange) {
//     return fallback;
//   }
//   if (!timeRange.raw) {
//     return { ...timeRange, raw: timeRange };
//   }

//   return timeRange;
// };

export default function SelectDashboards() {
  const dispatch = useDispatch();
  const { control } = useFormContext<ReportBaseV2>();
  const {
    fields: dashboards,
    append: addDashboard,
    remove: removeDashboard,
  } = useFieldArray({
    control: control,
    name: 'dashboards',
  });

  useEffect(() => {
    const defaultDashboard = dashboards[0];
    if (defaultDashboard && !isEmptyDashboard(defaultDashboard) && defaultDashboard.reportVariables) {
      dispatch(initVariables(defaultDashboard.dashboard?.uid!, defaultDashboard.reportVariables));
    }
  }, [dashboards, dispatch]);

  return (
    <ReportSection label={t('share-report.dashboard.section-title', 'Dashboard')}>
      <Stack direction="column" gap={2}>
        {dashboards.map((dashboard, index) => {
          return (
            <Stack direction="column" key={dashboard.id}>
              <SelectDashboard
                index={index}
                dataTestId={selectors.components.reportForm.selectDashboard(index.toString())}
                onRemoveClick={() => removeDashboard(index)}
              />
              {index < dashboards.length - 1 && <Divider spacing={0} />}
            </Stack>
          );
        })}
      </Stack>
      <Divider />
      <Button type="button" variant="primary" fill="text" onClick={() => addDashboard(defaultDashboard)}>
        + Add dashboard
      </Button>
    </ReportSection>
  );
}

export const SelectDashboard = ({ index, dataTestId, onRemoveClick }: SelectDashboardProps) => {
  const dispatch = useDispatch();

  const styles = useStyles2(getStyles);
  const theme = useTheme2();
  const isTimeRangeReversed = useMedia(`(max-width: ${theme.breakpoints.values.md}px)`);

  const [isTemplateVariablesOpen, setIsTemplateVariablesOpen] = useState(false);

  const { watch, control, setValue } = useFormContext<ReportBaseV2>();
  const dashboards = watch('dashboards');

  const dashboard = watch(`dashboards.${index}.dashboard`);
  const dashboardVariables = watch(`dashboards.${index}.reportVariables`);
  const dashboardTimeRange = watch(`dashboards.${index}.timeRange`);

  const dashboardUid = dashboard?.uid;
  const timeRange = getRange(dashboardTimeRange);

  const variables = dashboardUid ? getVariablesByKey(dashboardUid) : [];
  const visibleVariables = variables.filter((v) => v.hide !== VariableHide.hideVariable);

  const isDuplicate = dashboards.filter(({ dashboard }) => dashboard?.uid === dashboardUid).length > 1;
  const firstIndex = dashboards.findIndex(({ dashboard }) => dashboard?.uid === dashboardUid);
  const hideVariables = isDuplicate && firstIndex !== index;

  const onTimeRangeChange = (timeRange: RawTimeRange) => {
    if (refreshOnTimeRange(variables)) {
      initVariables(dashboardUid!, dashboardVariables, timeRange);
    }
  };

  const onDashboardChange = (dashboard: DashboardPickerDTO | undefined, uid?: string) => {
    // setValue(`dashboards.${index}.timeRange`, { from: '', to: '' });
    dispatch(initVariables(dashboard?.uid!, dashboardVariables));
  };

  return (
    <Stack direction="column" flex={1}>
      <Stack alignItems="center" flex={1} direction={{ xs: 'column', md: 'row' }}>
        <div className={styles.sourceDashboard}>
          <Field label="Source dashboard" required className={styles.field}>
            <Controller
              name={`dashboards.${index}.dashboard`}
              control={control}
              render={({ field: { onChange, ref, value, ...fieldProps } }) => {
                return (
                  <DashboardPicker
                    {...fieldProps}
                    id={`dashboard-${index}`}
                    data-testid={dataTestId}
                    aria-label={'Source dashboard'}
                    isClearable
                    value={value?.uid}
                    disabled={!canEditReport}
                    onChange={(dashboard) => {
                      onChange({ uid: dashboard?.uid, name: dashboard?.title });
                      onDashboardChange(dashboard);
                    }}
                  />
                );
              }}
            />
          </Field>
        </div>
        <Field label="Time range" disabled={!canEditReport} className={styles.field}>
          <Controller
            control={control}
            name={`dashboards.${index}.timeRange` as const}
            render={({ field: { ref, value, onChange, ...field } }) => {
              return (
                <TimeRangeInput
                  {...field}
                  value={makeTimeRange(timeRange.from, timeRange.to)}
                  onChange={(timeRange) => {
                    onChange(timeRange);
                    onTimeRangeChange(timeRange.raw);
                  }}
                  isReversed={isTimeRangeReversed}
                  clearable
                />
              );
            }}
          />
        </Field>
        <Stack alignItems="center">
          <LinkButton
            href={`${config.appUrl}d/${dashboardUid}`}
            target="_blank"
            icon="external-link-alt"
            variant="secondary"
            fill="text"
            tooltip="View dashboard"
          />
          {dashboards.length > 1 && (
            <IconButton key="delete" name="trash-alt" tooltip="Delete this dashboard" onClick={onRemoveClick} />
          )}
        </Stack>
      </Stack>
      {!!visibleVariables.length &&
        (hideVariables ? (
          <Alert
            severity="info"
            title={t(
              'share-report.dashboard.repeated-template-variables-description',
              'When adding the same dashboard multiple times in one report, template variables that you selected first are applied to all instances of that dashboard in the report.'
            )}
          ></Alert>
        ) : (
          <CollapsableSection
            label={t('share-report.dashboard.template-variables-title', 'Customize template variables')}
            isOpen={isTemplateVariablesOpen}
            onToggle={() => setIsTemplateVariablesOpen((prevState) => !prevState)}
            className={styles.templateVariablesSectionTitle}
            contentClassName={styles.templateVariablesContent}
          >
            <Stack direction="row" gap={1}>
              {visibleVariables.map((variable) => {
                const { picker: Picker, setValue: updateVariable } = variableAdapters.get(variable.type);
                return (
                  <Field label={variable.name} key={variable.name} className={styles.field}>
                    <Picker
                      variable={variable}
                      readOnly={false}
                      onVariableChange={(updated: VariableModel) => {
                        if (hasOptions(updated) && !isEmptyObject(updated.current)) {
                          // TODO WHAT ABOUT THIS? is it necessary
                          updateVariable(updated, updated.current);
                          setValue(`dashboards.${index}.reportVariables`, toReportVariables([updated]), {
                            shouldDirty: true,
                          });
                        }
                      }}
                    />
                  </Field>
                );
              })}
            </Stack>
          </CollapsableSection>
        ))}
    </Stack>
  );
};

const getStyles = (theme: GrafanaTheme2) => {
  return {
    sourceDashboard: css({
      flex: 1,
      width: '100%',
      [theme.breakpoints.up('md')]: {
        width: 'auto',
      },
    }),
    field: css({
      width: '100%',
      [theme.breakpoints.up('md')]: {
        width: 'auto',
      },
    }),
    sectionTitle: css({
      fontSize: theme.typography.h3.fontSize,
    }),
    templateVariablesSectionTitle: css({
      fontSize: theme.typography.h6.fontSize,
      color: theme.colors.text.primary,
    }),
    templateVariablesContent: css({
      paddingBottom: theme.spacing(0),
    }),
  };
};
