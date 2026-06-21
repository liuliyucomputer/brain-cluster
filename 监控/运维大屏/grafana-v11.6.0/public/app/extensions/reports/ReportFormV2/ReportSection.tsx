import { css, cx } from '@emotion/css';
import { useState } from 'react';

import { GrafanaTheme2 } from '@grafana/data';
import { CollapsableSection, useStyles2 } from '@grafana/ui';

export default function ReportSection({
  label,
  children,
  contentClassName,
  dataTestId,
  defaultOpen = false,
}: {
  label: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  contentClassName?: string;
  dataTestId?: string;
}) {
  const styles = useStyles2(getStyles);
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const onToggle = () => {
    setIsOpen((prevState) => !prevState);
  };

  return (
    <CollapsableSection
      isOpen={isOpen}
      onToggle={onToggle}
      label={label}
      className={styles.sectionTitle}
      contentClassName={cx(styles.content, contentClassName)}
      headerDataTestId={dataTestId}
    >
      {children}
    </CollapsableSection>
  );
}

const getStyles = (theme: GrafanaTheme2) => {
  return {
    sectionTitle: css({
      fontSize: theme.typography.h4.fontSize,
    }),
    content: css({
      paddingBottom: theme.spacing(0),
    }),
  };
};
