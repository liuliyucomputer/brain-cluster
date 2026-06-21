import { Report, ReportSchedulingFrequency } from '../../types';

export const getButtonText = (schedule?: Report['schedule']) => {
  if (!schedule) {
    return 'Save report';
  }
  if (schedule.frequency === ReportSchedulingFrequency.Never) {
    return 'Save and exit';
  } else if (schedule.startDate) {
    return 'Schedule send';
  } else {
    return 'Send now';
  }
};
